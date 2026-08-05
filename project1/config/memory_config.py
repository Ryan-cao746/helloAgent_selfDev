from pydantic import BaseModel


class MemoryConfig(BaseModel):

    working_memory_capacity: int = 0
    working_memory_ttl: int = 0
    database_path: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    def __init__(self,
                 working_memory_capacity:int = 0,
                 working_memory_ttl:int = 0 # ttl机制，即短期工作记忆存在一个生存周期，周期过后会被清除
                 ):
        super().__init__(
            working_memory_capacity = working_memory_capacity,
            working_memory_ttl = working_memory_ttl
        )