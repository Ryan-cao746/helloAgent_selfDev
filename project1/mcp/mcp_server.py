"""
基于FastMCP库的示例MCP实现
注意，里面的各个方法是对server里的mcp操作的，给它加上各种tools等，最后传给client的是server.mcp
"""
from typing import Optional, Callable, Literal, Any, Dict, Self

from fastmcp import FastMCP


class MCPServer:
    """基于FastMCP库的示例MCP实现"""

    def __init__(
            self,
            name:str,
            description:Optional[str] = None,
    ):
        """初始化MCP服务器"""
        self.mcp = FastMCP(name=name)
        self.name = name
        self.description = description or f"{name} MCP Server"

    def add_tool(
            self,
            func:Callable,
            name:Optional[str] = None,
            description: Optional[str] = None,
                 ):
        """将工具添加到服务器
        func:工具函数
        """
        # 使用装饰器注册工具
        if name or description:
            self.mcp.tool(name=name, description=description)(func) # mcp.tool函数返回一个装饰器wrapper，然后wrapper(func)调用这个装饰器
            # 一个函数返回了另一个函数，然后马上调用，这是链式调用，也就是装饰器模式
        else:
            self.mcp.tool()(func)

    def add_resource(
            self,
            func:Callable,
            name:Optional[str] = None,
            description: Optional[str] = None,
            uri: Optional[str] = None,
    ):
        """添加资源到服务器
        func:资源处理函数
        """
        if uri:
            self.mcp.resource(uri)(func)
        else:
            print("资源的uri不可以不填")
            raise(ValueError("资源的uri不可以不填"))

    def add_prompt(
            self,
            func: Callable,
            name: Optional[str] = None,
            description: Optional[str] = None
    ):
        """
        添加提示词模板到服务器

        Args:
            func: 提示词生成函数
            name: 提示词名称（可选）
            description: 提示词描述（可选）
        """
        # 使用装饰器注册提示词
        if name or description:
            self.mcp.prompt(name=name, description=description)(func)
        else:
            self.mcp.prompt()(func)

    def run(
            self,
            transport:Literal["stdio", "http", "sse", "streamable-http"] = "stdio", **kwargs
            ):
        """运行服务器

        Args:
            transport: 传输方式 ("stdio", "http", "sse")
            **kwargs: 传输特定的参数
                - host: HTTP 服务器主机（默认 "127.0.0.1"）
                - port: HTTP 服务器端口（默认 8000）
                - 其他 FastMCP.run() 支持的参数

        Examples:
            # Stdio 传输（默认）
            server.run()

            # HTTP 传输
            server.run(transport="http", host="0.0.0.0", port=8081)

            # SSE 传输
            server.run(transport="sse", host="0.0.0.0", port=8081)
        """
        self.mcp.run(transport=transport, **kwargs)

    def get_info(self) -> Dict[str, Any]:
        """
                获取服务器信息

                Returns:
                    服务器信息字典
                """
        return {
            "name": self.name,
            "description": self.description,
            "protocol": "MCP"
        }

class MCPServerBuilder:
    """MCP服务构建器，提供链式API
    链式API（Fluent API / Method Chaining），是一种面向对象编程中的设计风格，其核心特征是：让同一个对象的多个方法调用，像锁链一样连写在一起，一气呵成。
    它的底层原理非常简单：每个方法在执行完操作后，都返回当前对象本身（return this;）
    """

    def __init__(
            self,
            name: str,
            description: Optional[str] = None,
    ):
        self.server = MCPServer(name=name, description=description)

    def with_tool(self, func: Callable, name: Optional[str] = None,
                  description: Optional[str] = None) -> Self:
        """添加工具（链式调用）"""
        self.server.add_tool(func, name, description)
        return self

    def with_resource(self, func: Callable, uri: Optional[str] = None, name: Optional[str] = None,
                      description: Optional[str] = None) -> Self:
        """添加资源（链式调用）"""
        self.server.add_resource(func, name=name, description=description, uri=uri)
        return self

    def with_prompt(self, func: Callable, name: Optional[str] = None,
                    description: Optional[str] = None) -> Self:
        """添加提示词（链式调用）"""
        self.server.add_prompt(func, name, description)
        return self

    def build(self) -> MCPServer:
        """构建服务器"""
        return self.server

    def run(self):
        """构建并运行服务器"""
        self.server.run()

