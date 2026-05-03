from abstract import Parent, Container, Content
from tkinter import Text, Listbox, Menu, Event, NORMAL, DISABLED, END


class Context(Text, Parent):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<<Modified>>", self.edited)
        self.child = None

    def edited(self, *_):
        if self.child:
            self.child._content = self.get("1.0", "end-1c")
            self.child.update(self)
            self.edit_modified(False)

    def view(self, item: Content):
        if self.child:
            self.child.parents.remove(self)
        self.child = None
        self.update(item)
        self.child = item
        item.parents.append(self)

    def update(self, item: Content):
        self.enable()
        self.replace("1.0", END, item.content)
        if not item.editable:
            self.disable()
        self.see(END)

    def enable(self):
        self.config(state=NORMAL)

    def disable(self):
        self.config(state=DISABLED)


class Stack(Listbox, list[Content], Parent):
    def __init__(self, master, viewer: Parent, **kwargs):
        Listbox.__init__(self, master, **kwargs)
        list.__init__(self)
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Button-3>", self._menu)
        self.viewer = viewer
        self.dragging = None
        self.default = {}

    def _menu(self, event: Event):
        menu = Menu(self, tearoff=0)
        idx = self.nearest(event.y)
        if idx >= 0:
            self.select(idx)
            menu.add_command(label="Delete", command=lambda: self.pop(idx))
        elif self.default:
            draft = Menu(self, tearoff=0)
            for l, c in self.default.items():
                draft.add_command(label=l, command=lambda c=c: self.append(c()))
            menu.add_cascade(label="Draft", menu=draft)
        menu.post(event.x_root, event.y_root)

    def _click(self, event: Event):
        idx = self.nearest(event.y)
        if idx >= 0:
            self.dragging = [False, idx, (event.x, event.y)]
            self.select(idx)
        return "break"

    def _move(self, event: Event):
        if self.dragging:
            if self.dragging[0]:
                self.dragging[2] = (event.x, event.y)
                idx = self.nearest(event.y)
                pre = self.dragging[1]
                if 0 <= idx != pre:
                    self.insert(idx, self.pop(pre))
                    self.dragging[1] = idx
                self.dragging[0] = False
            else:
                x, y = self.dragging[2]
                dx, dy = event.x - x, event.y - y
                if (dx**2 + dy**2) > 16:
                    self.dragging[0] = True
        return "break"

    def _release(self, event: Event):
        self.dragging = None
        return "break"

    def select(self, idx: int):
        self.selection_clear(0, END)
        self.selection_set(idx)
        self.viewer.view(self[idx])

    def update(self, item: Content):
        idx = self.index(item)
        if self.title(idx) != item.title:
            self.set(idx, item.title)

    def view(self, item: Container[Content]):
        while self:
            self.pop(0)
        for i in item:
            self.append(i)

    def insert(self, idx: int, item: Content):
        Listbox.insert(self, idx, item.title)
        item.parents.append(self)
        list.insert(self, idx, item)

    def append(self, item: Content):
        self.insert(len(self), item)

    def pop(self, index=-1):
        Listbox.delete(self, index)
        self[index].parents.remove(self)
        return list.pop(self, index)

    def index(self, item: Content) -> int:
        return list.index(self, item)

    def __getitem__(self, index: int) -> Content:
        return list.__getitem__(self, index)

    def title(self, index: int) -> str:
        return Listbox.get(self, index)

    def set(self, index: int, title: str):
        Listbox.delete(self, index)
        Listbox.insert(self, index, title)

    def nearest(self, y: int) -> int:
        idx = Listbox.nearest(self, y)
        if 0 <= idx:
            bbox = self.bbox(idx)
            if bbox and bbox[1] <= y < bbox[1] + bbox[3]:
                return idx
        return -1
