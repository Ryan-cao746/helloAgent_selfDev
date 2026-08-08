from project1.complex_agents.types.multi_asking_agent.multi_asking_agent import MultiAskingAgent
from project1.core.llm_client import HelloAgentsLLM
from project1.tools.built_in.example import ExampleTool
from project1.tools.registry import ToolRegistry
from project1.user_input_interface.cil_user_input import CilUserInput

if __name__ == "__main__":

    llm_client = HelloAgentsLLM()
    user_input_interface = CilUserInput()
    tool_registry = ToolRegistry()

    tool_registry.register_tool(ExampleTool())

    multi_asking_agent = MultiAskingAgent(
        name="MultiAskingAgent",
        llm_client=llm_client,
        user_input_interface=user_input_interface,
        tool_registry=tool_registry,
        debug_mode=False,
    )

    print(multi_asking_agent.run())