from dotenv import load_dotenv

from project1.agents.simple_agent import SimpleAgent
from project1.core.llm_client import HelloAgentsLLM
from project1.tools.built_in.example import ExampleTool
from project1.tools.registry import ToolRegistry

load_dotenv() # 本脚本目录及父目录查找.env

llm_client = HelloAgentsLLM()

# 测试基础对话
print("===测试基础对话===")
basic_agent = SimpleAgent(
    name="basic_agent",
    llm_client=llm_client,
    system_prompt="你是⼀个友好的AI助⼿，请⽤简洁明了的⽅式回答问题。"
)

response1 = basic_agent.run("你好，请介绍⼀下⾃⼰")
print(f"基础对话响应: {response1}\n")

# 测试工具
print("===测试工具调用===")
tool_registry = ToolRegistry()
example_tool = ExampleTool()
tool_registry.register_tool(example_tool)

enhanced_agent = SimpleAgent(
    name="enhanced_agent",
    llm_client=llm_client,
    tool_registry=tool_registry,
    enable_tool_calling=True,
    system_prompt="你是⼀个智能助⼿，可以使⽤⼯具来帮助⽤户。"
)

response2 = enhanced_agent.run("帮我查询北京的天气")
print(f"增强对话响应: {response2}\n")