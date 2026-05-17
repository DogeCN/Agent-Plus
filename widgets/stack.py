from tkinter import Listbox, Menu, Event, END
from abstract import Host, Container, Content
from .config import UI
from .base import Base

T = Container[Content]


class Stack(Listbox, Base, Host[T]):

    def __init__(self, master, viewer: Host):
        Listbox.__init__(self, master)
        Host.__init__(self)
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)
        self.dragging = None
        self.viewer = viewer

    def _update(self):
        Listbox.delete(self, 0, END)
        for i in self.inner:
            Listbox.insert(self, END, i.title)
        self.tail()

    def _insert(self, index: int, item: Content):
        Listbox.insert(self, index, item.title)

    def _delete(self, index: int):
        Listbox.delete(self, index)

    def _click(self, event: Event):
        index = self.nearest(event.y)
        if index >= 0:
            self.dragging = [False, index, (event.x, event.y)]
            self.select(index)
        return "break"

    def _move(self, event: Event):
        if self.dragging:
            if self.dragging[0]:
                self.dragging[2] = (event.x, event.y)
                index = self.nearest(event.y)
                pre = self.dragging[1]
                if 0 <= index != pre:
                    self.inner.insert(index, self.inner.pop(pre))
                    self.dragging[1] = index
                self.dragging[0] = False
            else:
                x, y = self.dragging[2]
                dx, dy = event.x - x, event.y - y
                if (dx**2 + dy**2) > 16:
                    self.dragging[0] = True
        return "break"

    def _release(self, *_):
        self.dragging = None
        return "break"

    @property
    def current(self) -> int | None:
        selected = self.curselection()
        if selected:
            return selected[0]

    def append(self, item: Content):
        self.inner.append(item)

    def select(self, index: int):
        self.selection_clear(0, END)
        self.selection_set(index)
        self.viewer.host(self.inner[index])

    def pop(self, index=-1):
        return self.inner.pop(index)

    def tail(self):
        Listbox.see(self, END)
        if self.inner:
            self.select(-1)

    def nearest(self, y: int) -> int:
        index = Listbox.nearest(self, y)
        if 0 <= index:
            bbox = self.bbox(index)
            if bbox and bbox[1] <= y < bbox[1] + bbox[3]:
                return index
        return -1


class Edit:
    def __init__(self, stack: Stack):
        stack.bind("<Button-3>", self.show)
        self.draft = Menu(stack, tearoff=0)
        self.delete = Menu(stack, tearoff=0)
        self.stack = stack

    def append(self, c: type[Content], *args: object):

        def draft(c=c, args=args):
            self.stack.append(c(*args))
            self.stack.tail()

        self.draft.add_command(label=c.title, command=draft)

    def show(self, event: Event):
        selected = self.stack.current
        if selected is None:
            self.draft.post(event.x_root, event.y_root)
        else:
            self.delete.delete(0, END)
            self.delete.add_command(
                label=UI.Menu.DELETE, command=lambda: self.stack.pop(selected)
            )
            self.delete.post(event.x_root, event.y_root)
