from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from client import Client, Manager, Completion
from parts import Response, Search
from process import pwsh

console = Console()


class Message(Completion):
    type T = Message

    def update(self, chunk: str):
        super().update(chunk)
        live.update(Text(str(self)), refresh=True)
        if isinstance(self.tail, Response) and self.tail.action:
            return True

    def wrap(self, query: str):
        return Message(self, query)

    def send(self) -> T:
        message: Message = manager.send(self)
        action = message.tail.action
        if action:
            timeout, command = action
            message = message.wrap("")
            for line in pwsh(command, timeout):
                message.query += line
            message = message.send()
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
