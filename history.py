from tunnel import Tunnel, Mark


class Part:
    def __init__(self, mark: Mark):
        self.mark = mark
        self.content = ""


class Message:
    def __init__(self, query: str):
        self.parts: list[Part] = []
        self.query = query

    def update(self, chunk: str):
        tail = self.parts[-1]
        tail.content += chunk


class History:
    model = "default"
    thinking = False
    search = False

    def __init__(self):
        self.tunnels: list[Tunnel] = []
        self.messages: list[Message] = []
        self.index = 0

    def add(self, tunnel: Tunnel):
        self.tunnels.append(tunnel)

    def send(self, message: Message):
        self.messages.append(message)
        while True:
            current = self.tunnels[self.index]
            self.index = (self.index + 1) % len(self.tunnels)
            result = current.send(self.messages, self.model, self.thinking, self.search)
            mark = None
            for chunk in result:
                message.update(chunk)
                yield message.parts
            self.messages.append(message)
            if message.cycle:
                message.pool.shutdown()
                yield
            else:
                break
