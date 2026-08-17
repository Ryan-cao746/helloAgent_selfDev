"""提供兼容 OpenAI Chat Completions 接口的统一模型客户端。"""

import os

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import ValidationError
from typing import Callable, List

from project1.core.agent_protocol import AgentDecision, parse_agent_decision
from project1.core.exceptions import LLMClientError
from project1.core.message import Message

load_dotenv()

class HelloAgentsLLM:
    """调用兼容 OpenAI 接口的模型，并校验结构化 Agent 决策。"""
    def __init__(self, model:str = None, api_key: str = None, base_url: str = None, timeout:int = None, debug_mode:bool = False):
        """初始化客户端；显式参数优先于对应的环境变量。"""
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout = timeout or os.getenv("LLM_TIMEOUT", 60)
        self.debug_mode = debug_mode

        if self.debug_mode:
            print(self.model)
            print(self.base_url)
            # print(self.api_key)

        if not all([self.model, self.api_key, self.base_url]):
            raise ValueError("模型ID和API密钥和服务地址必须被提供或在.env文件中定义")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)

    def think(self, messages:List[Message], temperature: float = 0)->str :
        """流式调用模型并将响应片段合并为完整文本。"""
        if self.debug_mode:
            print(f"正在调用{self.model}模型")
        try:
            response = self.client.chat.completions.create(
                model = self.model,
                messages = [msg.to_dict() for msg in messages],
                temperature = temperature,
                stream=True
            )
            if self.debug_mode:
                print("大语言模型响应成功")
            collected_content = []
            for chunk in response:
                # 部分流式分块仅包含元数据，没有可追加的文本。
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                if self.debug_mode:
                    print(content, end="", flush=True)
                collected_content.append(content)
            print()
            return "".join(collected_content)

        except Exception as e:
            raise LLMClientError("调用LLM API或处理响应时发生错误") from e

    def decide(
            self,
            messages: List[Message],
            temperature: float = 0,
            max_retries: int = 1,
            on_retry: Callable[[str], None] | None = None,
    ) -> AgentDecision:
        """请求结构化决策；协议校验失败时按配置向模型反馈并重试。"""
        if max_retries < 0:
            raise ValueError("max_retries 不能小于 0")

        decision_messages = list(messages)

        for attempt in range(max_retries + 1):
            response = self.think(decision_messages, temperature=temperature)
            try:
                return parse_agent_decision(response)
            except ValidationError as error:
                if attempt >= max_retries:
                    raise LLMClientError("模型未返回合法的 Agent 决策 JSON") from error

                if on_retry is not None:
                    on_retry("模型返回的决策未通过协议校验")

                decision_messages.extend([
                    Message(content=response, role="assistant"),
                    Message(
                        content=(
                            "上一次响应不符合 Agent 决策协议。"
                            f"校验错误：{error}\n"
                            "请只返回一个合法 JSON 对象，不要输出 Markdown 或其他文字。"
                        ),
                        role="user",
                    ),
                ])

        raise LLMClientError("无法获得 Agent 决策")

# --- 客户端使用示例 --- #
if __name__ == "__main__":
    try:
        llmClient = HelloAgentsLLM()

        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "写一个快速排序算法"}
        ]

        print("--- 调用LLM ---")
        responseText = llmClient.think(exampleMessages)
        if(responseText):
            print("\n\n--- 完整响应模型 ---")
            print(responseText)

    except (ValueError, LLMClientError) as e:
        print(e)
