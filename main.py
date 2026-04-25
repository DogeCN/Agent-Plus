from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from client import Client, Manager, Completion, Search, Response
from re import compile, search
from process import pwsh

console = Console()

live = Live(console=console, auto_refresh=False)
live.start()


class Message(Completion):
    def update(self, chunk: str):
        super().update(chunk)
        live.update(Text(str(self)), refresh=True)


client_1 = Client("hark2009lbf@outlook.com")
client_1.login("hark123456")
client_2 = Client("13431218421")
client_2.login("Doge091218")

manager = Manager()
manager.thinking = True
manager.search = True
manager.tunnels.append(client_1.new())
manager.tunnels.append(client_2.new())

pattern = compile(r"<shell\s+timeout=(\d+)>([^<]+)</shell>")


def send(message: Message) -> Message:
    matched = search(pattern, manager.send(message).tail.content)
    if matched:
        timeout = matched.group(1)
        if timeout:
            timeout = int(timeout)
        code = matched.group(2)
        message = send(Message(message, pwsh(code, timeout=timeout)))
    return message


message = Message(open("prompt.md", "r").read(), "Introduce yourself briefly.")
while True:
    query = console.input("[bold blue]>> [/]")
    message = Message(message, query)
