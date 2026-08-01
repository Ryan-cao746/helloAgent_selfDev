from typing import Optional
import re
from project1.agents.prompt_template import REACT_PROMPT_TEMPLATE
from project1.core.agent import Agent
from project1.core.config import Config
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.tools.registry import ToolRegistry


class ReactAgent(Agent):
    """推理-行动"""
    def __init__(
            self,
            name:str,
            llm_client:HelloAgentsLLM,
            tool_registry:ToolRegistry,     # 工具注册表
            system_prompt:Optional[str]=None,
            config:Optional[Config]=None,   # 框架级配置
            max_steps: int = 5,     # 自定循环执行次数
            custom_prompt:Optional[str]=None    # 自定义提示词模板
    ):
        super().__init__(name, llm_client, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.message = [] # 工作记忆
        self.prompt_template = custom_prompt if custom_prompt else REACT_PROMPT_TEMPLATE
        print(f"初始化完成，最大步数{max_steps}")

    # override run方法
    def run(self, input_text:str, **kwargs) -> str :
        """跑ReAct"""
        self.message = []
        current_step = 0
        print(f"\n {self.name} 开始处理 {input_text}")

        while current_step < self.max_steps:    # loop
            current_step += 1
            print(f"-----第{current_step}步-----")

            # 提示词构建
            tool_description = self.tool_registry.get_tools_description() # 获取关于所有工具的详细描述，包括参数等
            history_str_list = [str(rec) for rec in self.message] # 先手动转换成字符串列表。因为前面写了__str__，所以这里str()不会出错
            history_str = "\n".join(history_str_list)
            prompt = self.prompt_template.format(tool_description=tool_description, history_str=history_str, input_text = input_text)
            print(prompt)

            # 调用LLM
            response = self.llm_client.think([Message(content=prompt, role="user")], **kwargs) # 这里由于本人的私下修改，导致think必须用Message类

            # 解析输出。先解析出thought和action，再从action中解析出tool_call
            thought, action = self._phrase_output(response)

            # 检查完成条件
            if action and action.startswith("Finish"):
                final_answer = self._phrase_action(action)[1] # 元组取第二个，即方括号里的
                self.add_message(Message(content=input_text, role="user")) # 计入长期记忆
                self.add_message(Message(content=final_answer, role="assistant"))
                return final_answer

            # 执行工具调用
            if action:
                tool_name, tool_input = self._phrase_action(action)
                if self.tool_registry is None:
                    return "似乎不存在工具注册表"
                result = self.tool_registry.execute_tool_call(tool_name, tool_input)
                self.message.append(Message(content=input_text, role="user")) # 计入工作记忆
                self.message.append(Message(content=result, role="tool"))

            else:
                print("似乎不存在工具调用")
        # 达到最大步数
        final_answer = "已达到最大迭代次数，无法完成任务。"
        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=final_answer, role="assistant"))
        return final_answer

    # 两个字符串模式匹配的工具方法
    def _phrase_output(self, text:str):
        """提取thought和action"""
        # Thought要匹配到Action:或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL) # 跳过 Thought: 后面可能存在的空白。非贪婪、条件地捕获内容直到Action:或文末。re.DOTALL指让正则表达式中的点号（.）匹配包括换行符（\n）在内的任意字符。

        # Action要匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _phrase_action(self, action_text:str):
        """从action里提取tool_calls"""
        match = re.match(r"(\w+)\[(.*)]", action_text, re.DOTALL) # 方括号前和后的分别为两个捕获组
        if match:
            return match.group(1), match.group(2)
        return None, None