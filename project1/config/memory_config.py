from pathlib import Path

from pydantic import BaseModel


class MemoryConfig(BaseModel):

    working_memory_capacity: int = 0
    working_memory_ttl: int = 0
    project_root: Path = Path(".")
    library_root: Path = Path("./memory_lib")
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
        self.project_root = self.get_project_root()
        self.library_root = self.get_library_root()

    @staticmethod
    def get_project_root() -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists():  # 或 .git / setup.py / requirements.txt
                return parent
        raise FileNotFoundError("项目根目录未找到，请检查标志性文件")

    def get_library_root(self) -> Path:
        if (self.project_root / "memory_lib").exists(): return self.project_root / "memory_lib"
        raise FileNotFoundError("语义记忆存储位置未找到")

if __name__ == "__main__":
    print(MemoryConfig.get_project_root())