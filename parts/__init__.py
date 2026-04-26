from .parser import Parser


class Search:
    def __init__(self, queries: list[str]):
        self.queries = queries


class Think:
    def __init__(self, content: str):
        self.content = content

    def update(self, chunk: str):
        self.content += chunk


class Response(Think):
    action = None

    def __init__(self, content: str):
        super().__init__(content)
        self.parser = Parser()
        for c in content:
            self.parser.update(c)

    def update(self, chunk: str):
        super().update(chunk)
        for c in chunk:
            if self.parser.update(c):
                self.action = self.parser.get()
