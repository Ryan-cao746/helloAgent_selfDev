"""同步封装 MCP 客户端，供同步工具执行管线调用。

主线程 start()
  -> _ready.clear()
  -> 启动后台线程
  -> _ready.wait()  阻塞等待

后台线程
  -> 创建 asyncio loop
  -> 执行 _start_client_async()
       -> 成功：self._client = MCPClient(...)
       -> 失败：self._startup_error = error
       -> finally: _ready.set()

主线程被唤醒
  -> 如果 _startup_error 不为空，抛 RuntimeError
  -> 否则说明 MCP client 已经连接好

"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from threading import Event, Thread, get_ident
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP

from project1.mcp_integration.mcp_client import MCPClient

"""
凡是没有被放在 target= 指定的子线程函数内部的代码，默认都由“主线程”执行。
所以每个线程是可以单独调用Event中的wait()来阻塞当前线程的
但是Event不支持唤醒某个单独线程，只支持全部唤醒
"""

class SyncMCPClientBridge:
    """在后台事件循环中维护 MCP 连接，并暴露同步调用方法。"""

    def __init__(
            self,
            server_source: Union[str, List[str], FastMCP, Dict[str, Any]],
            server_args: Optional[List[str]] = None,
            transport_type: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            **transport_kwargs: Any,
    ):
        self.server_source = server_source
        self.server_args = server_args
        self.transport_type = transport_type
        self.env = env
        self.transport_kwargs = transport_kwargs

        self._client: MCPClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None     # Python asyncio 库中事件循环（Event Loop）的抽象基类
        # 这个_loop值是子线程的loop，放到这里是用来让主线程控制
        self._thread: Thread | None = None
        self._thread_id: int | None = None
        self._ready = Event()   # Event对象，跨线程共享的开关，用于线程间简单通信。主线程创建一个 Event 对象，此时内部标志默认为 False
        self._startup_error: BaseException | None = None
        self._closed = False

    def start(self) -> None:
        """启动后台事件循环并建立 MCP 连接；重复调用是安全的。"""
        if self._client is not None:
            return
        if self._closed:
            raise RuntimeError("MCP 同步桥已经关闭，不能重新启动")

        self._ready.clear() # 调用 event.clear() 将所有标志重置为 False。
        self._startup_error = None
        self._thread = Thread(
            target=self._run_loop_thread,
            name="sync-mcp-client-bridge",
            daemon=True,    # 守护进程，持续运行直到主线程关闭
        )   # 将目标函数通过 target 参数传入。即线程启动时 run() 调用的可调用对象
        self._thread.start()    #启动事件循环，开启新线程，让这个任务在后台独立运行，主线程代码继续往下走，不等待。
        # 区别于run()，run会直接在当前线程（比如主线程）里执行这个函数，必须等函数执行完，才会执行下一行代码
        self._ready.wait()  # 阻塞主线程，等待后台的子线程创建好以及mcp_client创建完成，之后无论是否连接成功都会放开。这是后话。
        # 主要是防止主线程在后台loop运行前直接调用list_tools

        if self._startup_error is not None:
            self.close()    # 如果报错，关闭MCP连接等，最终阻塞和关闭子线程
            raise RuntimeError("启动 MCP 同步桥失败") from self._startup_error

    def list_tools(self) -> list[dict[str, Any]]:
        """同步列出 MCP server 中注册的 tools。"""
        return self._submit(self._list_tools_async)

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """同步调用一个 MCP tool。"""
        return self._submit(lambda: self._call_tool_async(tool_name, arguments))

    def list_resources(self) -> list[dict[str, Any]]:
        """同步列出 MCP server 中注册的 resources。"""
        return self._submit(self._list_resources_async)

    def read_resource(self, uri: str) -> Any:
        """同步读取一个 MCP resource。"""
        return self._submit(lambda: self._read_resource_async(uri))

    def list_prompts(self) -> list[dict[str, Any]]:
        """同步列出 MCP server 中注册的 prompts。"""
        return self._submit(self._list_prompts_async)

    def get_prompt(
            self,
            prompt_name: str,
            arguments: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """同步获取一个 MCP prompt。"""
        return self._submit(
            lambda: self._get_prompt_async(prompt_name, arguments)
        )

    def close(self) -> None:
        """关闭 MCP 连接、停止后台事件循环并等待线程退出。"""
        self._closed = True
        loop = self._loop
        thread = self._thread

        # 跨线程（多线程 + asyncio）环境下，优雅关闭异步客户端和事件循环的经典模板
        if loop is not None and loop.is_running():
            if self._client is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self._close_client_async(),
                    loop,
                )   #它将异步关闭客户端的协程提交给子线程中的 loop 去执行，并返回一个 concurrent.futures.Future 对象用于同步等待结果。
                # 将 self._close_client_async() 这个协程函数包装成一个 asyncio.Task 挂载到目标 loop 上。
                future.result() # 主线程同步阻塞等待子线程返回结果
            loop.call_soon_threadsafe(loop.stop)

        if thread is not None and thread.is_alive():
            thread.join() # 阻塞子线程

        self._client = None
        self._loop = None
        self._thread = None
        self._thread_id = None

    def __enter__(self) -> "SyncMCPClientBridge":
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _run_loop_thread(self) -> None:
        """单独创建的子线程运行的函数"""
        loop = asyncio.new_event_loop() # 创建一个全新的事件循环实例，新建一个独立的“异步任务调度器”。此时它不属于本线程
        self._loop = loop   # 把该loop放出来，方便主线程控制
        self._thread_id = get_ident()   # 返回一个非零整数，作为当前线程的“线程标识符”。
        asyncio.set_event_loop(loop)    # 指定的事件循环对象，绑定到当前线程的本地存储中，使其成为该线程的“默认事件循环”。
        loop.create_task(self._start_client_async())    # 封装一个协程，并将其加入到事件循环loop中

        try:
            loop.run_forever()  # 启动事件循环并使其持续运行，直到显式调用 loop.stop() 为止。
        finally:
            # Asyncio 优雅关闭（Graceful Shutdown） 的标准模板
            pending = asyncio.all_tasks(loop)   # 获取当前事件循环中所有尚未完成的任务（Task 对象
            for task in pending:
                task.cancel()   # 向所有任务发送取消请求。
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)    # 并发等待所有任务完成取消流程。
                )
            loop.close() # 关闭事件循环，释放其内部的 I/O 选择器（Selector）等系统资源。必须在所有任务彻底结束后调用，否则可能报错或内存泄漏。

    async def _start_client_async(self) -> None:
        """子线程事件循环维护的协程"""
        try:
            self._client = MCPClient(
                self.server_source,
                server_args=self.server_args,
                transport_type=self.transport_type,
                env=self.env,
                **self.transport_kwargs,
            )
            await self._client.__aenter__() # 启动上下文
        except BaseException as error:
            self._startup_error = error
            self._client = None
            loop = asyncio.get_running_loop()
            loop.call_soon(loop.stop)
        finally:
            self._ready.set()   # 无论是否发生异常，最后都唤醒所有因为调用 wait() 而阻塞的线程。这里是唤醒主线程

    async def _close_client_async(self) -> None:
        """由主线程挂载到子线程的loop上的函数，用来执行client的退出清理"""
        if self._client is None:
            return
        await self._client.__aexit__(None, None, None)
        self._client = None

    async def _list_tools_async(self) -> list[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.list_tools()

    async def _call_tool_async(
            self,
            tool_name: str,
            arguments: dict[str, Any],
    ) -> Any:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.call_tool(tool_name, arguments)

    async def _list_resources_async(self) -> list[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.list_resources()

    async def _read_resource_async(self, uri: str) -> Any:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.read_resource(uri)

    async def _list_prompts_async(self) -> list[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.list_prompts()

    async def _get_prompt_async(
            self,
            prompt_name: str,
            arguments: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        if self._client is None:
            raise RuntimeError("MCP 同步桥尚未连接")
        return await self._client.get_prompt(prompt_name, arguments)

    def _submit(
            self,
            coroutine_factory: Callable[[], Coroutine[Any, Any, Any]],
    ) -> Any:
        """同步桥接函数，向子线程的loop中添加新的协程。coroutine_factory是那个想要衔接的协程"""
        self.start() # 启动loop。因为重复调用是安全的，所以不用担心每次操作都start一边client的问题
        if self._loop is None:
            raise RuntimeError("MCP 同步桥事件循环尚未启动")
        if self._thread_id == get_ident():
            raise RuntimeError("不能从 MCP 同步桥的事件循环线程中同步等待协程")

        coroutine = coroutine_factory()
        future: Future[Any] = asyncio.run_coroutine_threadsafe(
            coroutine,
            self._loop,
        )   # 把这段协程加到子线程的loop中执行
        return future.result()
