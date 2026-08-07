from project1.agents.agent_types.base import Agent
from project1.complex_agents.types.multi_asking_agent.extract_json_from_answer import extract_json_from_answer
from project1.context.prompt_templates.summary_prompt_template import SUMMARY_PROMPT_TEMPLATE
from project1.core.llm_client import HelloAgentsLLM
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_item import MemoryItem

# 为记忆处理专门设计的摘要Agent
# 因为整体结构偏向简单，所以用这个基类

system_prompt = SUMMARY_PROMPT_TEMPLATE



class SummaryAgent(Agent):

    def __init__(
            self,
            name: str,
            llm_client: HelloAgentsLLM,
    ):
        super().__init__(
            name,
            llm_client,
        )

    def run(self, input_text: str, memory_manager: MemoryManager, **kwargs) -> str:
        """运行。这里提示词需要重做"""
        selected_episodic_memory = memory_manager.search(type="simple_episodic", query=input_text)  # 查询
        working_memory = memory_manager.get_all_by_type(type="simple_working")

        selected_episodic_memory_str = [f"- {memory.role}: {memory.content}" for memory in selected_episodic_memory]
        working_memory_str = [f"- {memory.role}: {memory.content}" for memory in working_memory_str]

        prompt = system_prompt.format(retrieved_memories=selected_episodic_memory_str, working_memory=working_memory_str)

        response = self.llm_client.think(prompt)

        data = extract_json_from_answer(response)
        ops = data.get("operations", [])
        if not ops:
            print("没有找到 operations 数组")
            return

        for op in ops:
            if op.get("operation", "N/A") == "UPDATE":
                memory_manager