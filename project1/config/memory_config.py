"""定义内存式记忆组件使用的容量、过期时间和目录配置。"""

from pathlib import Path

from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """记忆配置，并负责定位项目内的语义记忆资料目录。"""

    working_memory_capacity: int = 0
    working_memory_ttl: int = 0
    project_root: Path = Path(".")
    library_root: Path = Path("./memory_lib")
    database_path: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    def __init__(self,
                 working_memory_capacity:int = 0,
                 working_memory_ttl:int = 0
                 ):
        super().__init__(
            working_memory_capacity = working_memory_capacity,
            working_memory_ttl = working_memory_ttl
        )
        self.project_root = self.get_project_root()
        self.library_root = self.get_library_root()

    @staticmethod
    def get_project_root() -> Path:
        """从当前文件向上查找包含项目入口文件的目录。"""
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "main.py").exists():
                return parent
        raise FileNotFoundError("未找到包含 main.py 的项目目录")

    def get_library_root(self) -> Path:
        """返回项目内的语义记忆资料目录。"""
        if (self.project_root / "memory_lib").exists():
            return self.project_root / "memory_lib"
        raise FileNotFoundError("项目目录中不存在 memory_lib 语义记忆目录")

if __name__ == "__main__":
    print(MemoryConfig.get_project_root())
