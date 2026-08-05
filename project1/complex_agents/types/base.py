from abc import ABC, abstractmethod

from project1.core.llm_client import HelloAgentsLLM
from typing import Optional
from project1.config.config import Config
from project1.tools.registry import ToolRegistry


class BaseComplexAgent(ABC):

    def __init__(
            self,
            name:str,
            llm_client: HelloAgentsLLM,
            tool_registry: ToolRegistry = None,
            system_prompt: Optional[str] = None,
            config: Optional[Config] = None,
    ):
        self.name = name
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.config = config
        self.tool_registry = tool_registry
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent"""
        pass
