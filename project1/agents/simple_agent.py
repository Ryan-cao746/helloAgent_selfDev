# 最基础的agent实现
from typing import Optional, List
import re
from project1.core.agent import Agent
from project1.core.config import Config
from project1.core.message import Message
from project1.core.llm_client import HelloAgentsLLM
from project1.tools.registry import ToolRegistry


class SimpleAgent(Agent):
    """实现简单对话的agent"""

    def __init__(
            self,
            name: str,
            llm_client: HelloAgentsLLM,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
            tool_registry: Optional[ToolRegistry] = None,
            enable_tool_calling: bool = True
    ):
        super().__init__(name, llm_client, system_prompt, config) # 创建超类的对象并初始化
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None

        print(f"{name} 初始化完成，工具调用：{'启用' if self.enable_tool_calling else '禁用'}")

    # override run方法
    def run(self, input_text: str, max_tool_iterations: int = 3, **kwargs) -> str:
        """重写的方法，支持工具调用"""
        print(f"{self.name} 正在处理：{input_text}")

        messages = [] # 消息列表。说实话，这个消息列表有点奇怪，因为没有用Message类。我怀疑Message类不是用于传提示词的
        # 添加系统消息，包括工具信息
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append(Message(role=  "system", content= enhanced_system_prompt))
        # 将历史记录中所有信息灌到messages中。奇怪的是这里没有用Message类
        for msg in self.history:
            messages.append(msg) # 这里因为history和messages同类型，所以直接灌
        # 添加当前用户输入至消息中
        messages.append(Message(role=  "user", content= input_text))

        # 执行对话逻辑，调用api
        if not self.enable_tool_calling:
            # 不要求调用工具时直接think
            response = self.llm_client.think(messages, **kwargs)
            self.add_message(Message(input_text, "user")) #添加历史记录
            self.add_message(Message(response, "assistant"))
            print(f"{self.name} 响应完成")
            return response

        # 要求工具调用时
        return self._run_with_tools(messages, input_text, max_tool_iterations, **kwargs)

    def _get_enhanced_system_prompt(self) -> str: # 这玩意实际上就是一个简单的提示词工厂
        """增强系统提示词，主要是录入工具的信息"""
        base_prompt = self.system_prompt or "你是一个有用的AI助手"

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt # 若没有工具调用的需求，则直接返回基本的提示词

        #获取工具描述
        tools_description = self.tool_registry.get_tools_description()
        if not tools_description: # 无工具
            return base_prompt

        tools_section = f"""
        工具用name: type形式表示
        ## 可用工具
        你可以使用下列工具回答问题：
        {tools_description} 
        
        ## 工具调用格式
        当需要工具时，请使用如下格式：
        '[TOOL_CALL:{{tool_name}}:{{parameters}}]'
        例如：'[TOOL_CALL:search:Python编程]' 或 '[TOOL_CALL:memory:recall=⽤户信息]'
        
        ⼯具调⽤结果会⾃动插⼊到对话中，然后你可以基于结果继续回答。
        
        """
        return base_prompt + tools_section

    # 需要特别注意的是，这个方法是隶属于run方法的，也就是说它的message已经在run里注入好了input_text
    def _run_with_tools(self, messages: List, input_text:str, max_tool_iterations: int, **kwargs) -> str:
        """支持工具调用的运行逻辑"""
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations: # 这似乎是一个多次尝试的循环？每个循环掉用一次llm，这里message变量承担了记忆功能
            # 调llm
            response = self.llm_client.think(messages, **kwargs)
            # 从回答里解析tool_calls
            tool_calls = self._parse_tool_calls(response)
            if tool_calls:
                print(f"检测到{len(tool_calls)}个工具调用")
                # 执行所有tool_calls
                tool_results = []
                clean_response = response
                for tool_call in tool_calls:
                    result = self._execute_tool_call(tool_call['tool_name'], tool_call['parameters']) # 执行工具调用
                    tool_results.append(result) # 添加结果
                    clean_response = clean_response.replace(tool_call['original'], result) # 把llm响应串中的所有工具调用格式去掉
                # 记录消息，
                messages.append(Message(role=  "assistant", content= clean_response)) # 添加响应串
                # 添加工具执行结果
                tool_results_text = "\n\n".join(tool_results) # 将数组用换行符连接成完整字符串
                messages.append(Message(role=  "user", content= f"工具执行结果 \n{tool_results_text}\n"))

                #print(response) # debug打印
                current_iteration += 1
                continue
            # 若没有工具调用，直接当最终回答
            final_response = response
            break

        # 如果超过最大迭代次数，且最后一次仍然有tool_call，则还要最后生成一轮回答
        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm_client.think(messages, **kwargs)

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))
        print(f"{self.name} 响应完成")

        # 日志打印
        #print(messages)

        return final_response


    def _parse_tool_calls(self, text:str) -> List:
        """解析文本中的工具调用"""
        pattern = r'\[TOOL_CALL:([^:]+):([^\]]+)\]' # 正则表达式模式串。意思是第一个捕获组从:到:且不捕获:，第二个捕获组从:到]，且不捕获]
        matches = re.findall(pattern, text) # 找到段落中的所有tool_call

        tool_calls = []
        for tool_name, parameters in matches:
            tool_calls.append({
                'tool_name': tool_name.strip(), #去除首尾空白
                'parameters': parameters.strip(),
                'original': f'[TOOL_CALL:{tool_name}:{parameters}'
            })

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        """执行工具调用"""
        if not self.tool_registry:
            return f"错误，未配置工具注册表"

        try:
            # 这里改了，全用自动参数解析
            param_dict = self._parse_tool_parameters(parameters)
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                return f"未找到工具 {tool_name}"
            result = tool.run(param_dict)
            return f"工具{tool_name} 执行结果:\n {result}"
        except Exception as e:
            return f"工具执行失败:{str(e)}"

    def _parse_tool_parameters(self, parameters:str) -> dict:
        """智能解析工具参数"""
        param_dict = {} # 返回的是一个参数字典。这是很有趣的方法

        if '=' in parameters:
            # 匹配格式:key=value这种情况
            if ',' not in parameters:
                # 多参数情况，例如action=search,query=Python
                pairs = parameters.split(',') # 根据逗号划分捕获组
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1) # 根据等号划分键和值，最多划分一次
                        param_dict[key.strip()] = value.strip()
            else:
                # 单参数
                key, value = parameters.split('=', 1)  # 根据等号划分键和值，最多划分一次
                param_dict[key.strip()] = value.strip()
        else:
            print("参数格式不正确")

        return param_dict




