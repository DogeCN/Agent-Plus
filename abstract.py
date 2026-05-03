class Base:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type = cls.__name__


class Content[T](Base):
    def __init__(self, value: T):
        self.parents: list[Parent] = []
        self.editable = True
        self._title = self.type
        self._content = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, text: str):
        self._title = text
        self.update()

    @property
    def content(self) -> T:
        return self._content

    @content.setter
    def content(self, value: T):
        if self.editable:
            self._content = value
            self.update()

    def update(self, *exclude):
        for parent in list(self.parents):
            if parent not in exclude:
                parent.update(self)


class Parent:
    def view(self, item: Content): ...
    def update(self, item: Content): ...


class Container[T: Content](Content[list[T]]):
    def __init__(self, items: list[T] = []):
        super().__init__(items)

    def index(self, item: T) -> int:
        return self.content.index(item)

    def __len__(self):
        return len(self.content)

    def __getitem__(self, idx: int) -> T:
        return self.content[idx]

    def __setitem__(self, idx: int, item: T):
        self.content[idx] = item
        self.update()

    def __delitem__(self, idx: int):
        del self.content[idx]
        self.update()

    def append(self, item: T):
        self.content.append(item)
        self.update()


class Message(Container[Content[str]]):
    def __str__(self):
        return f"<｜{self.type}｜>{'\n'.join(map(str, self))}"


class Prompt(Content): ...


class System(Message):
    def __init__(self, content: str):
        super().__init__([Prompt(content)])


class Query(Content): ...


class User(Message):
    def __init__(self, content: str):
        super().__init__([Query(content)])


class Think(Content):
    def __init__(self, chunk: str):
        super().__init__(chunk)
        self.editable = False


class Search(Content):
    def __init__(self, queries: list[str]):
        super().__init__("\n".join(queries))
        self.editable = False
        self.queries = queries


class Response(Content): ...


class Assistant(Message):
    def __init__(self):
        super().__init__()
        self.links: dict[int, str] = {}

    def update(self, chunk: str):
        self[-1].content += chunk

    def link(self, id: int, link: str):
        if id not in self.links:
            self.links[id] = link
            self.update(f"[^{id}]")

    @property
    def footnote(self):
        return "\n".join([f"[^{id}]: {text}" for id, text in self.links.items()])

    def stop(self):
        self.update(f"\n\n{self.footnote}<｜end▁of▁sentence｜>")

    def __str__(self):
        return f"<｜{self.type}｜>{self[-1].content}"


class Messages(Container[Message]):
    def new(self):
        item = Assistant()
        self.append(item)
        return item

    def __str__(self):
        return "\n".join(map(str, self))
