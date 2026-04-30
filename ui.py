import tkinter as tk
from tkinter import ttk, font
from ctypes import windll

GEOMETRY = (0.5, 0.6)
TITLE = "Agent Plus"

try:
    windll.shcore.SetProcessDpiAwareness(2)
except:
    windll.shcore.SetProcessDpiAwareness()
root = tk.Tk()
root.title(TITLE)
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
width = int(screen_width * GEOMETRY[0])
height = int(screen_height * GEOMETRY[1])
root.geometry(f"{width}x{height}+{(screen_width-width)//2}+{(screen_height-height)//2}")
scale = root.winfo_fpixels("1i") / 72
root.tk.call("tk", "scaling", scale)
tkfont = font.nametofont("TkDefaultFont")
tkfont.configure(size=int(scale * 4))
root.option_add("*Font", tkfont)
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
style = ttk.Style()
style.theme_use("vista")

main = tk.Frame(root)
main.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)
main.grid_rowconfigure(0, weight=1)
main.grid_columnconfigure(0, weight=1)
main.grid_columnconfigure(1, weight=1)


class AbstractItem:
    def __init__(self, title: str):
        self.parents: list[AbstractParent] = []
        self.title = title
        self.content = ""

    def update(self):
        for parent in self.parents:
            parent.update(self)

    def __str__(self) -> str: ...


class AbstractParent:
    def update(self, item: AbstractItem): ...


class Content(tk.Text, AbstractParent):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<<Modified>>", self.edited)
        self.child = None

    def edited(self, *_):
        if self.child:
            self.child.content = self.get("1.0", "end-1c")
            self.edit_modified(False)
            # self.child.parents.remove(self)
            # self.child.update()
            # self.child.parents.append(self)

    def update(self, item: AbstractItem):
        if self.child:
            self.child.parents.remove(self)
        self.child = item
        self.delete("1.0", tk.END)
        self.insert(tk.END, str(item))
        item.parents.append(self)

    def destroy(self):
        self.child.parents.remove(self)
        tk.Text.destroy(self)


class Item(AbstractItem):
    @property
    def label(self):
        return self.title

    @label.setter
    def label(self, text: str):
        self.title = text
        self.update()

    @property
    def text(self):
        return self.content

    @text.setter
    def text(self, text: str):
        self.content = text
        self.update()

    def __str__(self) -> str:
        return self.content


class Stack(tk.Listbox, list[AbstractItem], AbstractParent):

    def __init__(self, master, viewer: Content, **kwargs):
        tk.Listbox.__init__(self, master, **kwargs)
        list.__init__(self)
        self.config(selectmode=tk.BROWSE)
        self.bind("<Button-1>", self._click)
        self.viewer = viewer

    @property
    def current(self) -> AbstractItem | None:
        selected = self.curselection()
        return self[selected[0]] if selected else None

    def _click(self, event: tk.Event):
        idx = self.nearest(event.y)
        self.selection_clear(0, tk.END)
        if idx >= 0:
            bbox = self.bbox(idx)
            if bbox and bbox[1] <= event.y < bbox[1] + bbox[3]:
                self.selection_set(idx)
                self.viewer.update(self[idx])
        return "break"

    def update(self, item: AbstractItem):
        self[self.index(item)] = item

    def append(self, item: AbstractItem):
        self.insert(tk.END, item.title)
        item.parents.append(self)
        list.append(self, item)

    def index(self, item: AbstractItem) -> int:
        return list.index(self, item)

    def __getitem__(self, index) -> AbstractItem:
        return list.__getitem__(self, index)

    def __setitem__(self, index, item: AbstractItem):
        self.delete(index)
        self.insert(index, item.title)
        self[index].parents.remove(self)
        list.__setitem__(self, index, item)
        item.parents.append(self)

    def __delitem__(self, index):
        self.delete(index)
        self[index].parents.remove(self)
        list.__delitem__(self, index)

    def remove(self, item: AbstractItem):
        del self[self.index(item)]

    def clear(self):
        for _ in range(len(self)):
            del self[0]

    def destroy(self):
        self.clear()
        tk.Listbox.destroy(self)


content = Content(main)
content.grid(row=0, column=1, padx=10, sticky=tk.NSEW)

stack = Stack(main, content)
stack.grid(row=0, column=0, padx=10, sticky=tk.NSEW)

messages = [
    ("user", "Hello"),
    ("assistant", "Hello, World!"),
    ("user", "Goodbye"),
    ("assistant", "Goodbye!"),
]

for role, msg in messages:
    item = Item(role)
    item.content = msg
    stack.append(item)

button = ttk.Button(main, text="Add")
button.grid(row=1, column=0, padx=10, sticky=tk.NSEW)


def add():
    item.text += "\nLAST"


button.config(command=add)

root.mainloop()
