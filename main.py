from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from client import Client, Manager, Completion, Search, Response
from re import S, compile, search
from process import pwsh

console = Console()


pattern = compile(r"<shell(?:\s+timeout=(\d+))?\s*>(.*?)</shell>", flags=S)


class Message(Completion):
    type T = Message

    def update(self, chunk: str):
        super().update(chunk)
        live.update(Text(str(self)), refresh=True)

    def wrap(self, query: str):
        return Message(self, query)

    def send(self) -> T:
        message = manager.send(self)
        matched = search(pattern, message.tail.content)
        if matched:
            timeout = matched.group(1)
            if timeout:
                timeout = int(timeout)
            code = matched.group(2)
            output = ""
            for line in pwsh(code, timeout=timeout):
                output += line
                live.update(Syntax(output, "powershell"))
            message = Message(message, output).send()
        return message


client_1 = Client("hark2009lbf@outlook.com")
client_1.login("hark123456")
client_2 = Client("13431218421")
client_2.login("Doge091218")

manager = Manager()
manager.thinking = True
manager.search = True
manager.tunnels.append(client_1.new())
manager.tunnels.append(client_2.new())


message = Message(
    open("prompt.md", "r", encoding="utf-8").read(), "Introduce yourself briefly."
)
while True:
    live = Live(console=console, auto_refresh=False, vertical_overflow="visible")
    live.start()
    message = message.send()
    live.stop()
    query = console.input("[bold blue]>> [/]")
    message = message.wrap(query)
