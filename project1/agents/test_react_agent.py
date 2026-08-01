from project1.agents.react_agent import ReactAgent
from project1.core.llm_client import HelloAgentsLLM
from dotenv import load_dotenv

from project1.tools.built_in.example import ExampleTool
from project1.tools.registry import ToolRegistry

load_dotenv()

llm_client = HelloAgentsLLM()
tool_registry = ToolRegistry()
example_tool = ExampleTool()
tool_registry.register_tool(example_tool)
react_agent = ReactAgent(name="react_agent", llm_client= llm_client, tool_registry=tool_registry, system_prompt="你是一个有用的、可以调用工具的助手")

result = react_agent.run("帮我查询北京的天气")

print(result)

print("历史记录：")
print(react_agent.history)
