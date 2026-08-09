
from project1.agents.types.base import BaseComplexAgent
from project1.agents.types.multi_asking_agent.extract_json_from_answer import extract_json_from_answer
from project1.context.prompt_templates.summary_prompt_template import SUMMARY_PROMPT_TEMPLATE
from project1.core.llm_client import HelloAgentsLLM
from project1.core.message import Message
from project1.memory.memory_manager import MemoryManager
from project1.memory.memory_types.memory_operation import MemoryOperationBatch

# 为记忆处理专门设计的摘要Agent
# 因为整体结构偏向简单，所以用这个基类

system_prompt = SUMMARY_PROMPT_TEMPLATE

class SummaryAgent(BaseComplexAgent):

    def __init__(
            self,
            llm_client: HelloAgentsLLM,
            memory_manager: MemoryManager,
            name: str = "summary_agent",
            debug_mode: bool = False,
    ):
        super().__init__(
            name,
            llm_client,
        )
        self.memory_manager = memory_manager
        self.debug_mode = debug_mode

    def run(self, input_text: str, **kwargs) -> str:
        """运行。这里提示词需要重做"""
        selected_episodic_memory = self.memory_manager.get_all_by_type(type=self.memory_manager.episodic_memory_name)
        working_memory = self.memory_manager.get_all_by_type(type=self.memory_manager.working_memory_name)

        selected_episodic_memory_str_list = [f"- 'id':'{memory.id}', 'role':'{memory.role}', 'content':'{memory.content}'" for memory in selected_episodic_memory]
        working_memory_str_list = [f"- 'id':'{memory.id}', 'role':'{memory.role}', 'content':'{memory.content}'" for memory in working_memory]

        selected_episodic_memory_str = "\n".join(selected_episodic_memory_str_list)
        working_memory_str = "\n".join(working_memory_str_list)

        prompt = system_prompt.format(retrieved_memories=selected_episodic_memory_str, working_memory=working_memory_str)

        response = self.llm_client.think([Message(content=prompt, role="user")])
        if self.debug_mode:
            print(response)

        data = extract_json_from_answer(response)

        # 先用operation_batch接受、构造、校验获取的json数组内容
        operation_batch = MemoryOperationBatch.model_validate(data) # 直接传入字典，自动解包，从任意对象提取数据，并启动整个校验引擎
        if not operation_batch.operations:
            print("没有找到 operations 数组")
            return  "没有找到 operations 数组"

        if self.debug_mode:
            print("====== 解析结果 ======")
            for operation in operation_batch.operations:
                print(
                    f"op_type={operation.operation},\n"
                    f"id={operation.target_id},\n"
                    f"content={operation.content}\n"
                )

        # memory_manager使用校验好的数据
        self.memory_manager.apply_operation_batch(
            type=self.memory_manager.episodic_memory_name,
            batch=operation_batch,
            add_role="user",
        )

        if self.debug_mode:
            print("====== 更改前情景记忆 ======")
            print(selected_episodic_memory_str)
            episodic_memories = self.memory_manager.get_all_by_type(type=self.memory_manager.episodic_memory_name)
            episodic_str_list = [memory.content for memory in episodic_memories]
            print("====== 更改后情景记忆 ======")
            print("\n".join(episodic_str_list))

        return "操作完成"

if __name__ == "__main__":
    from project1.memory.memory_types.simple_episodic_memory import SimpleEpisodicMemory
    from project1.memory.memory_types.simple_working_memory import SimpleWorkingMemory

    memory_manager = MemoryManager()
    episodic_memory_name = "episodic"
    working_memory_name = "working"

    memory_manager.add_new_memory_type(type=episodic_memory_name, base_memory=SimpleEpisodicMemory())
    memory_manager.add_new_memory_type(type=working_memory_name, base_memory=SimpleWorkingMemory())

    llm_client = HelloAgentsLLM()

    summary_agent = SummaryAgent(memory_manager=memory_manager, llm_client=llm_client, debug_mode=True,)

    memory_manager.add(type=episodic_memory_name, content="我叫李梅，是一名平面设计师", role="user")
    memory_manager.add(type=episodic_memory_name, content="我喝咖啡只加燕麦奶", role="user")
    memory_manager.add(type=episodic_memory_name, content="我对坚果过敏", role="user")

    memory_manager.add(type=working_memory_name, content="其实我姓王，不姓李。还有我现在喝咖啡换回全脂牛奶了", role="user")
    memory_manager.add(type=working_memory_name, content="收到，我记下了。", role="assistant")
    memory_manager.add(type=working_memory_name, content="那帮我看看附近有什么安静的咖啡店吧。", role="user")

    print(summary_agent.run("default"))
