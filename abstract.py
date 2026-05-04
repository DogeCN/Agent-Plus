class Base:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.type = cls.__name__


type Item = Container | Content


class Parent:
    def view(self, item: Item): ...
    def update(self, item: Item): ...


class Content[T](Base):
    def __init__(self, value: T):
        self.parents: list[Parent] = []
        self.editable = True
        self.content = value

    @property
    def title(self):
        return self.type

    @title.setter
    def title(self, value: str):
        self.type = value
        self.update()

    @property
    def value(self):
        return self.content

    @value.setter
    def value(self, value: T):
        self.content = value
        self.update()

    def update(self, *exclude):
        for parent in list(self.parents):
            if parent not in exclude:
                parent.update(self)


class Container[T: Content](Content[list[T]]):
    def __init__(self, items: list[T] = None):
        super().__init__(items or [])
        self.viewer: Parent = None
        self.editable = False

    def index(self, item: T) -> int:
        return self.content.index(item)

    def __len__(self):
        return len(self.content)

    def __getitem__(self, idx: int) -> T:
        return self.content[idx]

    def insert(self, idx: int, item: T):
        self.content.insert(idx, item)
        self.viewer.view(self)

    def append(self, item: T):
        self.insert(len(self), item)

    def pop(self, index=-1):
        item = self.content.pop(index)
        self.viewer.view(self)
        return item


class Message(Container[Content[str]]):
    def __str__(self):
        return f"<｜{self.type}｜>{self[-1].value}"


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

    def stream(self, chunk: str):
        self[-1].value += chunk

    def link(self, id: int, link: str):
        if id not in self.links:
            self.links[id] = link
            self.stream(f"[^{id}]")

    @property
    def footnote(self):
        return "\n".join([f"[^{id}]: {text}" for id, text in self.links.items()])

    def stop(self):
        self.stream("\n\n" + self.footnote)

    def __str__(self):
        return super().__str__() + "<｜end▁of▁sentence｜>"


class Messages(Container[Message]):
    def new(self):
        item = Assistant()
        self.append(item)
        return item

    def __str__(self):
        return "\n".join(map(str, self))
