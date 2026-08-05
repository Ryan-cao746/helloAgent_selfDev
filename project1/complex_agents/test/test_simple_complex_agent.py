from project1.complex_agents.types.simple_complex_agent import SimpleComplexAgent
from dotenv import load_dotenv

from project1.core.llm_client import HelloAgentsLLM
from project1.tools.registry import ToolRegistry
from project1.tools.built_in.example import ExampleTool

if __name__ == "__main__":
    load_dotenv()

    llm_client = HelloAgentsLLM()
    tool_registry = ToolRegistry()
    example_tool = ExampleTool()
    tool_registry.register_tool(example_tool)
    react_agent = SimpleComplexAgent(llm_client=llm_client, tool_registry=tool_registry)

    result = react_agent.run("帮我查询北京的天气")

    print(result)

    print("历史记录：")
    for memory in react_agent.memory_manager.memory_types["simple"].memories:
        print(memory.content)

