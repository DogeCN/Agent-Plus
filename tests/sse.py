from abstract import Assistant, Think, Search, Response
from json import loads


class Deepseek(Assistant):

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


message = Deepseek()
with open("tests/data.sse", encoding="utf-8") as f:
    for item in f:
        if item.startswith("data: "):
            data = loads(item[6:])
            if message.parse(data):
                break
print(message)
