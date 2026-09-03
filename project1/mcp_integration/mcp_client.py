from typing import Union, List, Any, Dict, Optional

try:
    from fastmcp import Client, FastMCP
    from fastmcp.client.transports import PythonStdioTransport, SSETransport, StreamableHttpTransport
    FASTMCP_AVAILABLE = True
except ImportError:
    raise ImportError(
        "fastmcp is required for MCP server functionality. "
        "Install it with: pip install fastmcp"
    )

"""
Python FastMCP的Client具有完善的上下文管理功能。
FastMCP的Client被设计为异步上下文管理器，这是官方推荐的使用方式。它主要通过async with语句来管理客户端的连接生命周期。
FastMCP Client的“上下文”（技术资源层）：指的是程序的运行生命周期。它管理的是网络连接、进程会话、内存缓冲区等底层资源。用async with client:的作用是确保你在用完客户端后，能正确关闭连接，避免内存泄漏或端口占用
所谓“上下文管理”即async with，类似同步的with.
with 是 Python 中的一个关键字，用于上下文管理协议（Context Management Protocol）。它简化了资源管理代码，特别是那些需要明确释放或清理的资源（如文件、网络连接、数据库连接等）。
使用async with 必须实现__aenter__ 和 __aexit__ 方法（这就是你上一个问题的答案），否则运行时报 TypeError。
因为__aenter__负责在进入async with 时获取和初始化资源，__aexit__负责在退出async with时释放资源、清理或处理异常。两者都是协程函数

协程是 asyncio 的核心概念之一。它是一个特殊的函数，可以在执行过程中暂停，并在稍后恢复执行。
协程通过 async def 关键字定义，并通过 await 关键字暂停执行，等待异步操作完成。
事件循环是 asyncio 的核心组件，负责调度和执行协程。它不断地检查是否有任务需要执行，并在任务完成后调用相应的回调函数。
通常用asyncio.run(协程函数())来执行一个事件循环，运行一个顶层协程。它不断地检查是否有任务需要执行，并在任务完成后调用相应的回调函数。
任务是对协程的封装，表示一个正在执行或将要执行的协程。你可以通过 asyncio.create_task(协程函数()) 函数创建任务，并将其添加到事件循环中。
Future 是一个表示异步操作结果的对象。它通常用于底层 API，表示一个尚未完成的操作。你可以通过 await 关键字等待 Future 完成。
如：future = asyncio.Future(); await future

这段代码似乎必须用async with或者单独调用__aenter__和__aexit__，因为连接到mcp_server是在__aenter__中

PythonStdioTransport
基于 标准输入/输出（Stdio） 的传输实现。
客户端会启动一个子进程来运行 MCP 服务器，然后通过子进程的 stdin 和 stdout 以 JSON-RPC 格式交换消息。

StreamableHttpTransport
基于 Streamable HTTP 协议的新一代 HTTP 传输实现。
客户端通过单一的 HTTP 端点（通常是 http://server:port/mcp）与服务器通信，使用标准的 POST/GET 请求发送 JSON-RPC 消息，并支持流式响应（通过可选 Server-Sent Events 实现）。

SSETransport
基于 旧版 HTTP + SSE（Server-Sent Events） 的传输实现（现已标记为遗留/弃用）。
客户端建立两条通道——一条 HTTP POST 用于发送请求，一条 SSE 连接用于接收服务器推送的消息。
"""

class MCPClient:
    """MCP客户端，支持多种传输方式"""

    def __init__(self,
                 server_source:Union[str, List[str], FastMCP, Dict[str, Any]],
                 server_args:Optional[List[str]] = None,
                 transport_type:Optional[str] = None,
                 env:Optional[Dict[str, str]] = None,
                 **transport_kwargs
                 ):
        """
        初始化MCP客户端
        参数：
            server_source:服务器源，支持多种格式：
                - FastMCP实例：内存传输
                - 字符串路径：Python脚本路径
                - Http URL: 远程服务器（如 "https://api.example.com/mcp"）
                - 命令列表：完整命令（如 ["python", "server.py"]）
                - 配置字典：传输配置
            server_args:服务器参数列表（可选）
            transport_type:强制指定传输类型
            env:环境变量字典
            **transport_kwargs:传输特定的额外参数
        """
        if not FASTMCP_AVAILABLE:
            raise ImportError(
                "Enhanced MCP client requires the 'fastmcp' library (version 2.0+). "
                "Install it with: pip install fastmcp>=2.0.0"
            )

        self.server_args = server_args or []
        self.transport_type = transport_type
        self.env = env or {}
        self.transport_kwargs = transport_kwargs
        self.client:Optional[Client] = None
        self.server_source = self._prepare_server_source(server_source)

    def _prepare_server_source(self, server_source: Union[str, List[str], FastMCP, Dict[str, Any]]):
        """解析提供的服务器源，根据类型创建合适的传输配置"""

        # 1.FastMCP实例-内存传输
        if isinstance(server_source, FastMCP):
            print(f"使用内存传输:{server_source.name}")
            return server_source

        # 2. 配置字典 - 根据配置创建传输
        if isinstance(server_source, dict):
            print(f"⚙️ 使用配置传输: {server_source.get('transport', 'stdio')}")
            return self._create_transport_from_config(server_source)

        # 3.HTTP URL - HTTP/SSE 传输
        if isinstance(server_source, str) and (
                server_source.startswith("http://") or server_source.startswith("https://")):
            transport_type = self.transport_type or "http"
            print(f"使用{transport_type.upper()}传输{server_source}")
            try:
                if transport_type == "sse":
                    return SSETransport(url=server_source, **self.transport_kwargs) # 如果传输类型特别指定是sse就使用sse传输的实现
                else:
                    return StreamableHttpTransport(url=server_source, **self.transport_kwargs)
            except Exception as e:
                print(f"创建http传输实现失败。 {e}")

        # 4.Python 脚本路径 - Stdio 传输
        if isinstance(server_source, str) and server_source.endswith(".py"):
            print(f"使用 stdio 传输 (Python): {server_source}")
            try:
                return PythonStdioTransport(
                    script_path=server_source,
                    args=self.server_args,
                    env=self.env if self.env else None,
                    **self.transport_kwargs
                )
            except Exception as e:
                print(f"创建stdio传输实现失败。 {e}")

        # 5.命令列表。这里不做了。

        # 6.其他情况 - 直接返回，让FastMCP自行判断
        print(f"自动推断传输: {server_source}")
        return server_source

    def _create_transport_from_config(self, config: Dict[str, Any]):
        """从配置字典创建传输"""
        transport_type = config.get("transport", "stdio")

        if transport_type == "stdio":
            # 检查是否是 Python 脚本
            args = config.get("args", [])
            if args and args[0].endswith(".py"):
                return PythonStdioTransport(
                    script_path=args[0],
                    args=args[1:] + self.server_args,
                    env=config.get("env"),
                    cwd=config.get("cwd"),
                    **self.transport_kwargs
                )
            else:
                # 使用通用 Stdio 传输
                from fastmcp.client.transports import StdioTransport
                return StdioTransport(
                    command=config.get("command", "python"),
                    args=args + self.server_args,
                    env=config.get("env"),
                    cwd=config.get("cwd"),
                    **self.transport_kwargs
                )
        elif transport_type == "sse":
            return SSETransport(
                url=config["url"],
                headers=config.get("headers"),
                auth=config.get("auth"),
                **self.transport_kwargs
            )
        elif transport_type == "http":
            return StreamableHttpTransport(
                url=config["url"],
                headers=config.get("headers"),
                auth=config.get("auth"),
                **self.transport_kwargs
            )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        print("连接到mcp服务器...")
        self.client = Client(self.server_source)
        self._context_manager = self.client
        await self._context_manager.__aenter__()    # 直接调用client的__aenter__
        print("连接成功")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._context_manager:
            await self._context_manager.__aexit__(exc_type, exc_val, exc_tb)
            self.client = None  # 清理资源
            self._context_manager = None
        print("连接已断开")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用的工具"""
        if not self.client:
            raise RuntimeError("未连接客户端。")
        result = await self.client.list_tools() # fastMCP自带的列出工具的方法

        # 处理不同的返回格式
        if hasattr(result, "tools"):    # 判断一个对象是否拥有指定的属性或方法。
            tools = result.tools
        elif isinstance(result, list):
            tools = result
        else:
            tools = []
        normalized_tools = []
        for tool in tools:
            input_schema = getattr(tool, "input_schema", None)
            if input_schema is None:
                input_schema = getattr(tool, "inputSchema", {})

            normalized_tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": input_schema,
                }
            )
        return normalized_tools

    async def call_tool(self, tool_name:str, arguments:Dict[str, Any]) -> Any:
        """调用MCP工具"""
        if not self.client:
            raise RuntimeError("未成功连接到mcp客户端")
        result = await self.client.call_tool(tool_name, arguments)  # 这个应该是mcp内置的方法

        # 解析结果 - FastMCP 返回 ToolResult对象
        if hasattr(result, "content") and result.content:
            if len(result.content) == 1:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                elif hasattr(content, "data"):
                    return content.data
            return [
                getattr(c, 'text', getattr(c, 'data', str(c)))
                for c in result.content
            ]
        return None

    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出所有可用的资源"""
        if not self.client:
            raise RuntimeError("未连接到mcp客户端")

        result = await self.client.list_resources()     # 这个应该也是mcp自带的方法
        return [
            {
                "uri": resource.uri,
                "name": resource.name or "",
                "description": resource.description or "",
                "mime_type": getattr(resource, "mimeType", None),
            }
            for resource in result
        ]

    async def read_resource(self, uri: str) -> Any:
        """读取资源内容"""
        if not self.client:
            raise RuntimeError("未连接mcp客户端")

        result = await self.client.read_resource(uri)

        # 解析资源内容
        if hasattr(result, 'contents') and result.contents:
            if len(result.contents) == 1:
                content = result.contents[0]
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'blob'):
                    return content.blob
            return [
                getattr(c, 'text', getattr(c, 'blob', str(c)))
                for c in result.contents
            ]
        return None

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有可用的提示词模板"""
        if not self.client:
            raise RuntimeError("未连接mcp客户端")

        result = await self.client.list_prompts()
        return [
            {
                "name": prompt.name,
                "description": prompt.description or "",
                "arguments": getattr(prompt, "arguments", []),
            }
            for prompt in result
        ]

    async def get_prompt(self, prompt_name:str, arguments: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """获取提示词内容"""
        if not self.client:
            raise RuntimeError("未连接mcp客户端")

        result = await self.client.get_prompt(prompt_name, arguments or {})

        # 解析提示词消息
        if hasattr(result, 'messages') and result.messages:
            return [
                {
                    "role":msg.role,
                    "content":getattr(msg.content, 'text', str(msg.content)) if hasattr(msg.content, 'text') else str(msg.content)
                }
                for msg in result.messages
            ]
        return []

    async def ping(self) -> bool:
        """测试服务器连接"""
        if not self.client:
            raise RuntimeError("未连接mcp客户端")

        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    def get_transport_info(self) -> Dict[str, Any]:
        """获取传输信息"""
        if not self.client:
            return {"status": "not_connected"}

        transport = getattr(self.client, 'transport', None)
        if transport:
            return {
                "status": "connected",
                "transport_type": type(transport).__name__,
                "transport_info": str(transport)
            }
        return {"status": "unknown"}
