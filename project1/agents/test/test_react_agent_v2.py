from project1.agents.types.react_agent_v2 import ReactAgentV2
from dotenv import load_dotenv

from project1.context.react_context_manager import ReActContextManager
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.tools.registry import ToolRegistry
from project1.tools.built_in.example import ExampleTool

if __name__ == "__main__":
    load_dotenv()

    episodic_memory_name = "simple_episodic"  # 改为注入名称，防止改名牵一发而动全身
    working_memory_name = "simple_working"

    llm_client = HelloAgentsLLM()
    tool_registry = ToolRegistry()
    example_tool = ExampleTool()
    tool_registry.register_tool(example_tool)
    memory_manager = MemoryManager(
        enable_working_memory=True,
        working_memory=SimpleWorkingMemory(),
        working_memory_name=working_memory_name,
        episodic_memory_name=episodic_memory_name,
    )
    context_manager = ReActContextManager(tool_registry=tool_registry, memory_manager=memory_manager)

    react_agent = ReactAgentV2(
        llm_client=llm_client,
        tool_registry=tool_registry,
        memory_manager=memory_manager,
        context_manager=context_manager,
    )

    result = react_agent.run("帮我查询北京的天气")

    print(result)

    print("历史记录：")
    for memory in react_agent.memory_manager.memory_types[working_memory_name].memories.values():
        print(memory.content)

