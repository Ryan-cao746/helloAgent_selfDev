from project1.agents.types.multi_asking_agent.multi_turn_conversation import MultiTurnConversation
from project1.agents.types.multi_asking_agent.summary_agent import SummaryAgent
from project1.agents.types.react_agent_v2 import ReactAgentV2
from project1.config.config import Config
from project1.config.memory_config import MemoryConfig
from project1.context.advanced_context_manager import AdvancedContextManager
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_episodic_memory import SimpleEpisodicMemory
from project1.memory.memory_types.simple_semantic_memory import SimpleSemanticMemory
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory
from project1.user_input_interface.base import UserInputInterface
from project1.tools.registry import ToolRegistry

def create_multi_turn_conversation(
    config: Config,
    user_input_interface: UserInputInterface,
    tool_registry: ToolRegistry,    # 工具类还是要外面提供的
) -> MultiTurnConversation:
    """专门构建多轮对话模型的工厂函数"""

    llm = HelloAgentsLLM()

    memory_cfg = MemoryConfig()

    memory_manager = MemoryManager(
        enable_working_memory=True,
        enable_episodic_memory=True,
        enable_semantic_memory=True,
        working_memory=SimpleWorkingMemory(),
        episodic_memory=SimpleEpisodicMemory(),
        sematic_memory=SimpleSemanticMemory(memory_cfg),
    )

    context_manager = AdvancedContextManager(
        memory_manager=memory_manager,
        tool_registry=tool_registry,
    )

    conversation_agent = ReactAgentV2(
        llm_client=llm,
        tool_registry=tool_registry,
        memory_manager=memory_manager,
        context_manager=context_manager,
        max_steps=config.max_steps,
    )

    summary_agent = SummaryAgent(
        llm_client=llm,
        memory_manager=memory_manager,
    )

    return MultiTurnConversation(
        user_input_interface=user_input_interface,
        memory_manager=memory_manager,
        conversation_agent=conversation_agent,
        summary_agent=summary_agent,
        max_ask=config.max_ask,
        debug_mode=config.debug,
    )