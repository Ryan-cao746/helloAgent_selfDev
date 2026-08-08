from project1.agents.agent_types.base import Agent
from project1.complex_agents.types.multi_asking_agent.extract_json_from_answer import extract_json_from_answer
from project1.context.prompt_templates.summary_prompt_template import SUMMARY_PROMPT_TEMPLATE
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.simple_episodic_memory import SimpleEpisodicMemory
from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory

# 为记忆处理专门设计的摘要Agent
# 因为整体结构偏向简单，所以用这个基类

system_prompt = SUMMARY_PROMPT_TEMPLATE

class SummaryAgent(Agent):

    def __init__(
            self,
            llm_client: HelloAgentsLLM,
            memory_manager: MemoryManager,
            episodic_memory_name:str = "episodic",   # 改为注入名称，防止改名牵一发而动全身
            working_memory_name:str = "working",
            name: str = "summary_agent",
            debug_mode: bool = False,
    ):
        super().__init__(
            name,
            llm_client,
        )
        self.episodic_memory_name = episodic_memory_name
        self.working_memory_name = working_memory_name
        self.memory_manager = memory_manager
        self.debug_mode = debug_mode

    def run(self, input_text: str, **kwargs) -> str:
        """运行。这里提示词需要重做"""
        selected_episodic_memory = self.memory_manager.get_all_by_type(type=self.episodic_memory_name)
        working_memory = self.memory_manager.get_all_by_type(type=self.working_memory_name)

        selected_episodic_memory_str_list = [f"- 'id':'{memory.id}', 'role':'{memory.role}', 'content':'{memory.content}'" for memory in selected_episodic_memory]
        working_memory_str_list = [f"- 'id':'{memory.id}', 'role':'{memory.role}', 'content':'{memory.content}'" for memory in working_memory]

        selected_episodic_memory_str = "\n".join(selected_episodic_memory_str_list)
        working_memory_str = "\n".join(working_memory_str_list)

        prompt = system_prompt.format(retrieved_memories=selected_episodic_memory_str, working_memory=working_memory_str)

        response = self.llm_client.think([Message(content=prompt, role="user")])
        if self.debug_mode:
            print(response)

        data = extract_json_from_answer(response)
        ops = data.get("operations", [])
        if not ops:
            print("没有找到 operations 数组")
            return  "没有找到 operations 数组"

        if self.debug_mode:
            print("====== 解析结果 ======")

        for op in ops:
            # 注意这里json解析的结果要和提示词上写的对应好了
            op_type = op.get("operation", "N/A")
            id = op.get("target_id", "N/A")
            content = op.get("summary", "N/A")

            if self.debug_mode:
                print(f"op_type={op_type},\nid={id},\ncontent={content}\n")

            if op_type == "UPDATE":
                self.memory_manager.update_memory_content(type=self.episodic_memory_name, id=id, new_content=content)
            elif op_type == "ADD":
                self.memory_manager.add(type=self.episodic_memory_name, content=content, role="assistant")
            elif op_type == "DELETE":
                self.memory_manager.delete_memory_by_type(type=self.episodic_memory_name, id=id)
            elif op_type == "NOOP":
                continue
            else:
                print(f"错误的操作类型 '{op_type}'")

        if self.debug_mode:
            print("====== 更改前情景记忆 ======")
            print(selected_episodic_memory_str)
            episodic_memories = self.memory_manager.get_all_by_type(type=self.episodic_memory_name)
            episodic_str_list = [memory.content for memory in episodic_memories]
            print("====== 更改后情景记忆 ======")
            print("\n".join(episodic_str_list))

        return "操作完成"

if __name__ == "__main__":
    memory_manager = MemoryManager()
    episodic_memory_name = "episodic"
    working_memory_name = "working"

    memory_manager.add_new_memory_type(type=episodic_memory_name, base_memory=SimpleEpisodicMemory())
    memory_manager.add_new_memory_type(type=working_memory_name, base_memory=SimpleWorkingMemory())

    llm_client = HelloAgentsLLM()

    summary_agent = SummaryAgent(memory_manager=memory_manager, llm_client=llm_client, debug_mode=True,
                                 episodic_memory_name=episodic_memory_name, working_memory_name=working_memory_name)

    memory_manager.add(type=episodic_memory_name, content="我叫李梅，是一名平面设计师", role="user")
    memory_manager.add(type=episodic_memory_name, content="我喝咖啡只加燕麦奶", role="user")
    memory_manager.add(type=episodic_memory_name, content="我对坚果过敏", role="user")

    memory_manager.add(type=working_memory_name, content="其实我姓王，不姓李。还有我现在喝咖啡换回全脂牛奶了", role="user")
    memory_manager.add(type=working_memory_name, content="收到，我记下了。", role="assistant")
    memory_manager.add(type=working_memory_name, content="那帮我看看附近有什么安静的咖啡店吧。", role="user")

    print(summary_agent.run("default"))