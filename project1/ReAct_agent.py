from project1.llm_client import HelloAgentsLLM
from project1.prompt_template import REACT_PROMPT_TEMPLATE
from project1.tools.tool_executor import ToolExecutor
import re #正则表达式操作模块

class ReActAgent:
    def __init__(self, llm_client:HelloAgentsLLM, tool_executor:ToolExecutor, max_steps:int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question:str): # run方法是智能体的入口，while循环构成了智能体的主体
        """
        运行ReAct来回答一个问题
        """
        self.history = [] # 每次运行时重置历史记录
        current_step = 0

        while current_step < self.max_steps: # max_steps是一个很重要的安全阀，防止智能体陷入无限循环
            current_step += 1
            print(f"--- 第 {current_step} 步 ---")

            # 1.格式化提示词
            tools_desc = self.tool_executor.get_available_tools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(question=question, tools_desc=tools_desc, history_str=history_str)

            # 2.向LLM发送请求
            messages = [{"role" : "user", "content" : prompt}]
            response_text = self.llm_client.think(messages=messages)

            if not response_text:
                print("错误:LLM未能有效响应。")
                break

    def _parse_output(self, text:str):
        """
        解析LLM的输出，提取Thought和Action
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)",
text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else ""
        action = action_match.group(1).strip() if action_match else ""
        return thought, action
        # \s* —— 匹配零个或多个空白字符（空格、制表符等）。
        # (.*?) —— 捕获组，非贪婪地匹配任意字符（. 可匹配换行，因为启用了 re.DOTALL），尽量少地匹配，直到遇到后面的限定条件。
        # (?=\nAction:|$) —— 正向先行断言，表示当前位置之后必须紧跟 换行符 + "Action:" 或者 字符串末尾，但不消耗这些字符，即它们不会被包含在匹配结果中。
        # 如果正则匹配成功（thought_match 不为 None），则取出第一个捕获组 group(1)（即括号内匹配的内容），用 .strip() 去除首尾空白；否则赋值为 None。

    def _parse_action(self, action_text:str):
        """
        解析Action字符串，提取工具名称和输入
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        # re.match是从头匹配，如果第一个字符不匹配就退出。而search是搜索，第一个不匹配不会退出

        if match:
            return match.group(1), match.group(2)
        else:
            return "", ""