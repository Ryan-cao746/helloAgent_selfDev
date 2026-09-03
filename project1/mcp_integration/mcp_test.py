from project1.mcp_integration.mcp_client import MCPClient
from project1.mcp_integration.mcp_server import MCPServer
import asyncio

def create_example_server() -> MCPServer:
    """创建一个示例的mcp服务器"""
    server = MCPServer(
        name="example_server",
        description="这是一个简单的mcp测试服务器"
    )

    server.add_tool(
        calculator,
        name="calculator",
        description="Calculate a math expression"
    )
    server.add_tool(
        greet,
        name="greet",
        description="Generate a friendly greeting"
    )

    return server

def calculator(expression:str) -> str:
    """计算数学表达式

            Args:
                expression: 要计算的数学表达式，例如 "2 + 2" 或 "10 * 5"
            """
    try:
        # 安全的表达式求值（仅支持基本运算）
        allowed_chars = set("0123456789+-*/() .")
        if not all(c in allowed_chars for c in expression):
            return f"Error: Invalid characters in expression"
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

# 添加一个问候工具
def greet(name: str) -> str:
    """生成友好的问候语

    Args:
        name: 要问候的人的名字
    """
    return f"Hello, {name}! Welcome to the MCP server example."

async def main():   # 只有在协程内部才能写await
    server = create_example_server()
    async with MCPClient(server_source=server.mcp) as client:   # 这里接受的参数不应是server，而是server.mcp这个FastMCP对象
        tools_list = await client.list_tools()
        for tool in tools_list:
            print(tool)

if __name__ == "__main__":
    asyncio.run(main())
