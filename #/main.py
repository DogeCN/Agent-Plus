from rich.console import Console, Group
from rich.live import Live
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Generator, Tuple, Optional, Dict, Any
from pathlib import Path
from fastmcp import Client
import json, json_repair
import urllib.request
import ctypes

console = Console()
API_BASE = "http://127.0.0.1:5001"
API_KEY = "doge"
MCP_SERVER_PATH = Path(__file__).parent / "mcp_server.py"
# 可用模型列表
AVAILABLE_MODELS = [
    "deepseek-chat",
    "deepseek-r1",
    "deepseek-chat-search",
    "deepseek-r1-search",
]
MODEL = AVAILABLE_MODELS[1]


def is_ctrl_pressed():
    VK_CONTROL = 0x11
    return ctypes.windll.user32.GetKeyState(VK_CONTROL) & 0x8000


def is_escape_pressed():
    VK_ESCAPE = 0x1B
    return ctypes.windll.user32.GetKeyState(VK_ESCAPE) & 0x8000


def multiline_input(prompt: str = "") -> str:
    console.print(prompt, end="")
    lines = []
    while True:
        line = console.input()
        lines.append(line)
        if is_escape_pressed():
            console.print("\n")
            return ""
        elif is_ctrl_pressed():
            break
        console.print("[dim]>>[/dim] ", end="")
    return "\n".join(lines)


def chat_stream(messages: list, tools: list) -> Generator[Tuple[str, Any], None, None]:
    """流式聊天请求"""
    body = {"model": MODEL, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_BASE}/v1/chat/completions", data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    full_text = ""
    reasoning_text = ""
    finish_reason = None
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except ValueError:
                continue
            choice = chunk.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason") or finish_reason
            delta = choice.get("delta", {})
            if delta.get("reasoning_content"):
                content = delta["reasoning_content"]
                reasoning_text += content
                yield "reasoning", content
            elif delta.get("content"):
                content = delta["content"]
                if content != "FINISHED":
                    full_text += content
                    yield "text", content
    yield "done", {
        "finish_reason": finish_reason,
        "content": full_text,
        "reasoning": reasoning_text,
    }


class MCPClientManager:
    """MCP 客户端管理器"""

    def __init__(self):
        self._client = None
        self._initialized = False

    async def start(self) -> bool:
        """启动 MCP 服务器并建立连接"""
        try:
            self._client = Client(MCP_SERVER_PATH)
            await self._client.__aenter__()
            console.print(f"[green]✓ MCP 服务器连接成功[/green]")
            self._initialized = True
            return True
        except Exception as e:
            console.print(f"[red]✗ MCP 服务器连接失败: {e}[/red]")
            return False

    async def stop(self):
        """停止 MCP 服务器"""
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception as e:
                console.print(f"[red]MCP 服务器关闭失败: {e}[/red]")
            self._client = None
        self._initialized = False

    async def get_tools(self) -> list:
        """获取 MCP 工具列表"""
        if not self._initialized:
            return []
        try:
            result = await self._client.list_tools()
            return [self._to_openai_tool(t) for t in result]
        except Exception as e:
            console.print(f"[red]获取工具列表失败: {e}[/red]")
            return []

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用 MCP 工具"""
        if not self._initialized:
            return "Error: MCP client not initialized"
        try:
            result = await self._client.call_tool(tool_name, arguments)
            return str(result.data)
        except Exception as e:
            console.print(f"[red]调用工具失败: {e}[/red]")
            return f"Error: {str(e)}"

    def _to_openai_tool(self, tool) -> dict:
        """将 MCP 工具转换为 OpenAI 格式"""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }

    def is_initialized(self) -> bool:
        return self._initialized


def display_welcome():
    """显示欢迎信息"""
    console.print()
    console.print(
        f"[bold cyan]MCP Demo Client[/bold cyan] | 模型: [yellow]{MODEL}[/yellow] | API: [dim]{API_BASE}[/dim]"
    )
    console.print(f"MCP 服务器: [dim]{MCP_SERVER_PATH}[/dim]")
    console.print()


def display_tools_help(tools: list):
    """显示工具帮助信息"""
    tool_names = [t["function"]["name"] for t in tools]
    console.print(
        f"[green]✓ 共 {len(tools)} 个MCP工具: {', '.join(tool_names)}[/green]"
    )


def display_commands_help():
    """显示命令帮助信息"""
    console.print(f"[bold]可用命令:[/bold]")
    console.print(f"  [yellow]exit[/yellow] - 退出程序")
    console.print(f"  [yellow]clear[/yellow] - 清空对话历史")
    console.print(f"  [yellow]help[/yellow] - 显示帮助信息")
    console.print()
    console.print(f"[bold]模型管理:[/bold]")
    console.print(f"  [yellow]model[/yellow] - 查看当前模型")
    console.print(f"  [yellow]model <name>[/yellow] - 切换模型")
    console.print(f"  [yellow]model list[/yellow] - 列出可用模型")
    console.print(f"  [cyan]当前模型: {MODEL}[/cyan]")
    console.print()
    console.print(f"[bold]记忆管理:[/bold]")
    console.print(f"  [yellow]mem store <key> <value>[/yellow] - 存储记忆")
    console.print(f"  [yellow]mem get <key>[/yellow] - 获取记忆")
    console.print(f"  [yellow]mem search <query>[/yellow] - 搜索记忆")
    console.print(f"  [yellow]mem list[/yellow] - 列出所有记忆")
    console.print(f"  [yellow]mem delete <key>[/yellow] - 删除记忆")
    console.print()


async def handle_model_command(user_input: str) -> bool:
    """处理模型切换命令，返回是否已处理"""
    global MODEL
    if not user_input.lower().startswith("model"):
        return False
    parts = user_input[5:].strip().split(None, 1)
    if not parts:
        console.print(f"[cyan]当前模型: {MODEL}[/cyan]")
        console.print()
        return True
    cmd = parts[0].lower()
    if cmd == "list":
        console.print(f"[bold]可用模型:[/bold]")
        for i, model in enumerate(AVAILABLE_MODELS, 1):
            marker = "[green]✓[/green]" if model == MODEL else " "
            console.print(f"  {marker} {i}. {model}")
        console.print()
        return True
    else:
        model_name = cmd
        if model_name.isdigit():
            index = int(model_name) - 1
            if 0 <= index < len(AVAILABLE_MODELS):
                MODEL = AVAILABLE_MODELS[index]
                console.print(f"[green]✓ 已切换到模型: {MODEL}[/green]")
                console.print()
            else:
                console.print(
                    f"[red]错误: 索引超出范围 (1-{len(AVAILABLE_MODELS)})[/red]"
                )
                console.print()
            return True
        if model_name in AVAILABLE_MODELS:
            MODEL = model_name
            console.print(f"[green]✓ 已切换到模型: {MODEL}[/green]")
            console.print()
        else:
            console.print(f"[red]错误: 未知模型 '{model_name}'[/red]")
            console.print(f"[yellow]可用模型: {', '.join(AVAILABLE_MODELS)}[/yellow]")
            console.print()
        return True


async def handle_memory_command(mcp_manager: MCPClientManager, user_input: str) -> bool:
    """处理记忆管理命令，返回是否已处理"""
    if not user_input.lower().startswith("mem"):
        return False
    parts = user_input[3:].strip().split(None, 1)
    if not parts:
        console.print("[yellow]记忆命令: mem store/get/search/list/delete[/yellow]")
        console.print()
        return True
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    if cmd == "store":
        if not args:
            console.print("[red]用法: mem store <key> <value>[/red]")
            console.print()
            return True
        store_parts = args.split(None, 1)
        if len(store_parts) < 2:
            console.print("[red]用法: mem store <key> <value>[/red]")
            console.print()
            return True
        key, value = store_parts
        result = await mcp_manager.call_tool(
            "memory_store", {"key": key, "value": value}
        )
        console.print(f"[green]{result}[/green]")
        console.print()
        return True
    elif cmd == "get":
        if not args:
            console.print("[red]用法: mem get <key>[/red]")
            console.print()
            return True
        result = await mcp_manager.call_tool("memory_retrieve", {"key": args})
        console.print(f"[cyan]{result}[/cyan]")
        console.print()
        return True
    elif cmd == "search":
        if not args:
            console.print("[red]用法: mem search <query>[/red]")
            console.print()
            return True
        result = await mcp_manager.call_tool("memory_search", {"query": args})
        console.print(result)
        console.print()
        return True
    elif cmd == "list":
        result = await mcp_manager.call_tool("memory_list", {})
        console.print(result)
        console.print()
        return True
    elif cmd == "delete":
        if not args:
            console.print("[red]用法: mem delete <key>[/red]")
            console.print()
            return True
        result = await mcp_manager.call_tool("memory_delete", {"key": args})
        console.print(f"[green]{result}[/green]")
        console.print()
        return True
    else:
        console.print(f"[red]未知命令: mem {cmd}[/red]")
        console.print("[yellow]可用命令: store, get, search, list, delete[/yellow]")
        console.print()
        return True


def display_streaming_response(messages: list, tools: list) -> Optional[Dict[str, Any]]:
    """显示流式响应"""
    content_text = ""
    reasoning_text = ""
    with Live(
        console=console, refresh_per_second=10, vertical_overflow="visible"
    ) as live:
        done_payload = None
        try:
            for typ, val in chat_stream(messages, tools):
                if typ == "reasoning":
                    reasoning_text += val
                elif typ == "text":
                    content_text += val
                elif typ == "done":
                    done_payload = val
                live.update(
                    Group(Text(reasoning_text, style="dim"), Markdown(content_text))
                )
        except KeyboardInterrupt:
            console.print("\n[yellow]✗ 已终止模型输出[/yellow]")
            # 返回部分结果
            done_payload = {
                "finish_reason": "user_cancelled",
                "content": content_text,
                "reasoning": reasoning_text,
            }
        except Exception as e:
            console.print(f"[red]请求失败: {e}[/red]")
            return None
    return done_payload


def display_tool_calls(tool_calls: list, turn: int):
    """显示工具调用信息"""
    console.print()
    console.print(
        f"[bold yellow]🔧 第 {turn + 1} 轮工具调用 ({len(tool_calls)} 个)[/bold yellow]"
    )
    for tc in tool_calls:
        console.print(
            Syntax(str(tc["function"]), "json", theme="github-dark", word_wrap=True)
        )


def display_tool_result(name: str, result: str):
    """显示工具执行结果"""
    result = result[:300] + ("..." if len(result) > 300 else "")
    console.print(f"[green]✓ {name}[/green]")
    console.print(result)


def display_conversation_stats(messages: list):
    """显示对话统计"""
    user_count = sum(1 for m in messages if m["role"] == "user")
    console.print(f"[dim]（对话轮数: {user_count}）[/dim]")
    console.print()


async def main():
    """主循环"""
    display_welcome()
    mcp_manager = MCPClientManager()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("正在连接到 MCP 服务器...", total=None)
        success = await mcp_manager.start()
    if not success:
        console.print("[red]无法连接到 MCP 服务器，退出程序[/red]")
        return
    tools = await mcp_manager.get_tools()
    tool_names = [t["function"]["name"] for t in tools]
    console.print(
        f"[green]✓ 已连接，共 {len(tools)} 个MCP工具: {', '.join(tool_names)}[/green]"
    )
    console.print()
    try:
        state = False
        console.print("[dim]初始化...[/dim]")
        while True:
            if state is False:
                await process(
                    'Convert `memory_retrieve("agent_persona")`,`memory_search("skill")`,`memory_retrieve("context")`,`memory_search("available")`,`memory_list(limit=50)` to standard `tool_calls` format to initialize the conversation.',
                    mcp_manager,
                    tools,
                    detailed=False,
                )
            try:
                user_input = multiline_input("[bold blue]>>[/bold blue] ").strip()
            except KeyboardInterrupt:
                break
            state = await process(user_input, mcp_manager, tools)
            if state:
                break
    finally:
        await mcp_manager.stop()


async def process(
    prompt: str,
    mcp_manager: MCPClientManager,
    tools: list,
    messages: list = [],
    detailed: bool = True,
):
    if (
        not prompt
        or await handle_model_command(prompt)
        or await handle_memory_command(mcp_manager, prompt)
    ):
        return
    if prompt.lower() == "exit":
        console.print("[yellow]退出程序[/yellow]")
        return True
    if prompt.lower() == "clear":
        messages.clear()
        console.print(Markdown("-----"))
        console.print()
        return False
    if prompt.lower() == "help":
        console.print()
        display_commands_help()
        console.print()
        display_tools_help(tools)
        console.print()
        return
    # 清理历史消息中的 FINISHED 状态码
    for msg in messages:
        if msg.get("role") in ["user", "assistant"]:
            msg["content"] = msg.get("content", "").replace("FINISHED", "")
    messages.append({"role": "user", "content": prompt})
    turn = 0
    while True:
        done_payload = display_streaming_response(messages, tools)
        if not done_payload:
            break
        finish_reason = done_payload["finish_reason"]
        if finish_reason == "user_cancelled":
            break
        full_content = done_payload["content"].replace("FINISHED", "")
        reasoning = done_payload["reasoning"].replace("FINISHED", "")
        assistant_msg = {"role": "assistant", "content": full_content}
        messages.append(assistant_msg)
        results = []
        try:
            if full_content and "tool_calls" in full_content:
                tool_calls = extract_tool_calls(full_content)
            elif reasoning and "tool_calls" in reasoning:
                tool_calls = extract_tool_calls(reasoning)
            else:
                break
        except Exception as e:
            results.append(f"Error parsing tool_calls: {e}. ")
            console.print(f"[red]解析失败: {e}[/red]")
            continue

        if detailed:
            display_tool_calls(tool_calls, turn)
        for tc in tool_calls:
            try:
                name = tc["function"]["name"]
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True,
                ) as progress:
                    progress.add_task(
                        f"正在调用 {name}... (按 Ctrl+C 终止)", total=None
                    )
                    args = tc["function"]["arguments"]
                    result = await mcp_manager.call_tool(name, args)
                    results.append(result)
                if detailed:
                    display_tool_result(name, result)
            except KeyboardInterrupt:
                console.print(f"[yellow]✗ 已终止 {name} 调用[/yellow]")
                results.append(
                    "Error: Tool call cancelled by user, maybe it got stuck."
                )
            except ValueError as e:
                console.print(f"[red]解析失败: {e}[/red]")
                results.append(f"Error: Failed to parse tool arguments: {e}")
        turn += 1
        for result in results:
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": result}
            )
    if detailed:
        display_conversation_stats(messages)


def extract_tool_calls(text: str) -> list:
    # Remove any FINISHED tokens that might have leaked
    text = text.replace("FINISHED", "").strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx : end_idx + 1]
    else:
        raise ValueError("no valid JSON object found")
    return json_repair.loads(text)["tool_calls"]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
