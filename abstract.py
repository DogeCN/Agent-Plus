class Base:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.title = cls.__name__


class Content[T](Base):

    def __init__(self, content: T):
        self.host: Host[T] | None = None
        self.editable = True
        self.content = content

    def update(self):
        if self.host:
            self.host._update()


class Host[T: Content]:

    def __init__(self):
        self.inner = None

    def host(self, inner: T):
        if self.inner:
            self.inner.host = None
        self.inner = inner
        self._update()
        inner.host = self

    def _update(self): ...
    def _insert(self, index: int, item: Content): ...
    def _delete(self, index: int): ...


class Container[T: Content](Content[list[T]]):
    def __init__(self, items: list[T] = None):
        super().__init__(items or [])
        self.editable = False

    def index(self, item: T) -> int:
        return self.content.index(item)

    def __len__(self):
        return len(self.content)

    def __bool__(self):
        return bool(self.content)

    def __getitem__(self, idx: int) -> T:
        return self.content[idx]

    def insert(self, index: int, item: T):
        self.content.insert(index, item)
        if self.host:
            self.host._insert(index, item)

    def append(self, item: T):
        self.insert(len(self), item)

    def pop(self, index=-1):
        item = self.content.pop(index)
        if self.host:
            self.host._delete(index)
        return item


class Part(Content[str]): ...


class Message[T: Part](Container[T]):
    @property
    def tail(self) -> T:
        return self[-1]

    def __str__(self): ...


class Messages[T: Message](Container[T]):
    def __str__(self): ...
