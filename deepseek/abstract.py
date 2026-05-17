from abstract import Part, Message, Messages


class DeepseekPart(Part):
    def link(self, id: str, title: str, url: str): ...
    def stream(self, chunk: str):
        self.content += chunk
        self.update()


class DeepseekMessage(Message[DeepseekPart]):
    mark: str

    def __str__(self):
        return f"<｜{self.mark}｜>{self.tail.content}" if self.tail.content else ""


class Prompt(DeepseekPart): ...


class System(DeepseekMessage):
    mark: str = "System"

    def __init__(self, content: str):
        super().__init__([Prompt(content)])


class Query(DeepseekPart): ...


class User(DeepseekMessage):
    mark: str = "User"

    def __init__(self, content: str):
        super().__init__([Query(content)])


class Think(DeepseekPart):
    def __init__(self, chunk: str):
        super().__init__(chunk)
        self.editable = False


class Search(DeepseekPart):
    def __init__(self, queries: list[str]):
        super().__init__("\n".join(queries))
        self.editable = False
        self.queries = queries


class Response(DeepseekPart):
    def __init__(self, chunk: str):
        super().__init__(chunk)
        self.body = ""
        self.footnote = ""
        self.ids = []

    def link(self, id: str, title: str, url: str):
        if id not in self.ids:
            self.ids.append(id)
            self.footnote += f"[^{id}]: [{title}]({url})\n"
            self.stream(f"[^{id}]")

    def stream(self, chunk: str):
        self.body += chunk
        self.content = self.body + "\n\n" + self.footnote
        self.update()


class Assistant(DeepseekMessage):
    mark: str = "Assistant"

    def __init__(self):
        super().__init__()
        self.cached = {}

    def parse(self, data: dict):
        v = data.get("v")
        if isinstance(v, list):
            for item in v:
                if self.parse(item):
                    return True
        elif isinstance(v, dict):
            return self.parse(v["response"]["fragments"][0])
        elif isinstance(v, str):
            p = data.get("p")
            if p == "quasi_status":
                return True
            if not p or "/content" in p:
                self.tail.stream(v)
        elif "type" in data:
            t = data["type"]
            content = data.get("content")
            if t == "TOOL_OPEN":
                id = data["id"]
                result = data.get("result")
                if result:
                    self.cached[id] = result
                elif id in self.cached:
                    result = self.cached[id]
                    self.tail.link(id, result["title"], result["url"])
            elif t == "TOOL_SEARCH" and "queries" in data:
                queries = [q["query"] for q in data["queries"]]
                self.append(Search(queries))
            elif t == "THINK" and content:
                self.append(Think(content))
            elif t == "RESPONSE" and content:
                self.append(Response(content))

    def __str__(self):
        return super().__str__() + "<｜end▁of▁sentence｜>"


class DeepseekMessages(Messages[DeepseekMessage]):
    def new(self):
        message = Assistant()
        self.append(message)
        return message

    def __str__(self):
        return "\n".join(map(str, self))
