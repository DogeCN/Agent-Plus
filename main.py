from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown
from client import Client, Mark
from messages import Manager, User, History

console = Console()

client_1 = Client("hark2009lbf@outlook.com")
client_1.login("hark123456")
client_2 = Client("13431218421")
client_2.login("Doge091218")

history = History(open("prompt.md", "r", encoding="utf-8").read())
manager = Manager(history)
manager.append(client_1.new())
manager.append(client_2.new())

manager.thinking = True
manager.search = True
while True:
    with Live(console=console, auto_refresh=False, vertical_overflow="visible") as live:
        for part in manager.send(User(console.input("[cyan]>> [/cyan]"))):
            current = None
            if part:
                group = []
                for block in part:
                    content = block.content
                    match block.mark:
                        case Mark.THINK:
                            group.append(Text(content, style="dim"))
                        case Mark.CODE:
                            group.append(Text(str(block)))
                        case Mark.RESPONSE:
                            group.append(Markdown(content))
                        case Mark.SEARCH:
                            group.append(Text(content, style="purple"))
                current = Group(*group)
                live.update(current, refresh=True)
            else:
                console.print(current)
