from abstract import Parent, Container, Content
from config import UI, MODELS, model, save
from tkinter import ttk
import tkinter as tk


class Context(tk.Text, Parent):
    def __init__(self, master, **kwargs):
        super().__init__(master, undo=True, **kwargs)
        self.bind("<<Modified>>", self.edited)
        self.child = None

    def edited(self, *_):
        if self.child and self.child.editable:
            self.child.content = self.get("1.0", "end-1c")
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
        self.replace("1.0", tk.END, item.value)
        if not item.editable:
            self.disable()
        self.see(tk.END)

    def enable(self):
        self.config(state=tk.NORMAL)

    def disable(self):
        self.config(state=tk.DISABLED)


class Stack(tk.Listbox, Parent):
    def __init__(self, master, viewer: Parent, **kwargs):
        tk.Listbox.__init__(self, master, **kwargs)
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Button-3>", self._menu)
        self.menu = tk.Menu(self, tearoff=0)
        self.container: Container[Content] = None
        self.viewer = viewer
        self.dragging = None

    def _menu(self, event: tk.Event):
        idx = self.nearest(event.y)
        if idx >= 0:
            self.select(idx)
        self.menu.post(event.x_root, event.y_root)

    def _click(self, event: tk.Event):
        idx = self.nearest(event.y)
        if idx >= 0:
            self.dragging = [False, idx, (event.x, event.y)]
            self.select(idx)
        return "break"

    def _move(self, event: tk.Event):
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

    def _release(self, *_):
        self.dragging = None
        return "break"

    def select(self, idx: int):
        self.selection_clear(0, tk.END)
        self.selection_set(idx)
        self.viewer.view(self[idx])

    def update(self, item: Content):
        idx = self.index(item)
        if self.title(idx) != item.type:
            self.set(idx, item.type)

    def view(self, container: Container[Content]):
        if self.container:
            tk.Listbox.delete(self, 0, tk.END)
            for i in self.container:
                if self in i.parents:
                    i.parents.remove(self)
            self.container.viewer = None
        self.container = container
        container.viewer = self
        for i in self.container:
            i.parents.append(self)
            tk.Listbox.insert(self, tk.END, i.type)
        self.tail()

    def insert(self, idx: int, item: Content):
        tk.Listbox.insert(self, idx, item.type)
        item.parents.append(self)
        self.container.insert(idx, item)

    def append(self, item: Content):
        self.insert(len(self.container), item)

    def pop(self, index=-1):
        tk.Listbox.delete(self, index)
        self[index].parents.remove(self)
        return self.container.pop(index)

    def delete(self):
        idx = self.curselection()
        if idx:
            self.pop(idx[0])
        elif self.container:
            self.pop()

    def index(self, item: Content) -> int:
        return self.container.index(item)

    def __getitem__(self, index: int) -> Content:
        return self.container[index]

    def title(self, index: int) -> str:
        return tk.Listbox.get(self, index)

    def set(self, index: int, title: str):
        tk.Listbox.delete(self, index)
        tk.Listbox.insert(self, index, title)

    def tail(self):
        tk.Listbox.see(self, tk.END)
        if self.container:
            self.select(-1)

    def nearest(self, y: int) -> int:
        idx = tk.Listbox.nearest(self, y)
        if 0 <= idx:
            bbox = self.bbox(idx)
            if bbox and bbox[1] <= y < bbox[1] + bbox[3]:
                return idx
        return -1


class Drafts(tk.Menu):
    def __init__(self, master: Stack):
        super().__init__(master, tearoff=0)
        master.menu.add_cascade(label=UI.Menu.DRAFT, menu=self)
        master.menu.add_command(label=UI.Menu.DELETE, command=self.delete)
        self.stack = master

    def append(self, c: type[Content], *args: object):

        def draft(c=c, args=args):
            self.stack.append(c(*args))
            self.stack.tail()

        self.add_command(label=c.type, command=draft)


class Toolbar(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.model = model["model"]
        self.thinking = model["thinking"]
        self.search = model["search"]

        self.modelBtn = tk.Button(self, text=self.model, command=self.next, width=15)
        self.modelBtn.grid(row=0, column=0, padx=5, pady=5)

        self.thinkingBtn = ttk.Checkbutton(
            self, text="Thinking", command=self.toggleThinking
        )
        self.thinkingBtn.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.set(self.thinkingBtn, self.thinking)

        self.searchBtn = ttk.Checkbutton(self, text="Search", command=self.toggleSearch)
        self.searchBtn.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.set(self.searchBtn, self.search)

    def next(self):
        model["model"] = (model["model"] + 1) % len(MODELS)
        self.model = MODELS[model["model"]]
        self.modelBtn.config(text=self.model)
        save()

    def toggleThinking(self):
        self.thinking = not self.thinking
        model["thinking"] = self.thinking
        self.set(self.thinkingBtn, self.thinking)
        save()

    def toggleSearch(self):
        self.search = not self.search
        model["search"] = self.search
        self.set(self.searchBtn, self.search)
        save()

    def set(self, btn: ttk.Checkbutton, state: bool):
        btn.state([("!" if state else "") + "selected"])
