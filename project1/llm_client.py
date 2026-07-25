import os

from openai import OpenAI
from dotenv import load_dotenv, find_dotenv  # 让你可以把配置项写在 .env 文件里，然后在代码中一键加载，让程序像读取系统环境变量一样去使用它们
from typing import List, Dict


load_dotenv() #加载.env文件中的内容

class HelloAgentsLLM:
    """
    定制的LLM客户端。用于调用任何兼容OpenAI接口的服务
    """
    def __init__(self, model:str = None, api_key: str = None, base_url: str = None, timeout:int = None):
        """
        初始化客户端。优先使用传入参数，若未提供则从环境变量加载。
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout = timeout or os.getenv("LLM_TIMEOUT", 60)

        print(self.model)
        print(self.base_url)
        print(self.api_key)

        if not all([self.model, self.api_key, self.base_url]):
            raise ValueError("模型ID和API密钥和服务地址必须被提供或在.env文件中定义")

        # 它负责管理与 OpenAI API 的认证、网络请求等。
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout)

    def think(self, messages:List[Dict[str, str]], temperature: float = 0)->str :
        """
        调用大语言模型进行思考，并返回其响应
        """
        print(f"正在调用{self.model}模型")
        try:
            response = self.client.chat.completions.create(
                model = self.model,
                messages = messages,
                temperature = temperature,
                stream=True
            )
            # OpenAI SDK 要求的是 ChatCompletionMessageParam：role 必须是 "user"、"assistant"、"system" 等特定字面值，并且不同角色有不同字段。content 也不一定是字符串，还可能是多模态内容列表或 None。
            # 所以这里会标黄，因为dict[str, str] 对键和角色的约束太宽，对值的约束又太窄。
            # PyCharm 会警告，因为它们无法从这个宽泛类型证明消息满足 SDK 的严格结构。
            # 所以直接把消息声明成 list[ChatCompletionMessageParam] 最合适。

            # response 是一个生成器（或可迭代对象），每次迭代返回一个流式响应块（chunk）。

            # chat：代表“对话”功能模块。
            # completions：代表“补全”子模块，专用于聊天补全（Chat Completion）。
            # create(...)：实际发出请求的方法，它会向 OpenAI 的 /v1/chat/completions 端点发送 HTTP 请求，并返回一个响应对象。

            # 处理流式响应
            print("大语言模型响应成功")
            collected_content = []
            for chunk in response:        # 每个 chunk 是 API 返回的一个 JSON 解析后的对象，通常带有 choices 字段。
                if not chunk.choices:     # 某些分块可能只包含元数据（如 role 定义、finish_reason 等），没有实际的文本内容（choices 为空）。跳过这些无效块，避免后续取 choices[0] 时出错。
                    continue
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)      # 立即刷新输出缓冲区，确保用户可以实时看到每个字，而不是等积累一定量才显示。这是流式输出“打字机效果”的关键。
                collected_content.append(content)
            print()
            return "".join(collected_content)           # 把本次的文本片段放入列表，用于最后组装完整答案。

        except Exception as e:
            print(f"调用LLM API时发生错误：{e}")
            return None

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

    except ValueError as e:
        print(e)