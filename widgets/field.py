from tkinter import Frame, Text, Scrollbar, NSEW, NS, NORMAL, DISABLED, END
from abstract import Host, Content
from .base import Base

T = Content[str]


class Field(Frame, Base, Host[T]):

    def __init__(self, master):
        Frame.__init__(self, master)
        Host.__init__(self)
        self.text = Text(self, undo=True)
        self.text.grid(row=0, column=0, sticky=NSEW)
        self.scrollbar = Scrollbar(self, command=self.text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=NS)
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.grid_columnconfigure(0, weight=1)
        self.text.bind("<<Modified>>", self.edited)

    def _update(self):
        self.text.config(state=NORMAL)
        self.text.replace("1.0", END, self.inner.content)
        if not self.inner.editable:
            self.text.config(state=DISABLED)
        self.text.see(END)

    def edited(self, *_):
        if self.inner and self.inner.editable:
            self.inner.content = self.text.get("1.0", "end-1c")
            self.text.edit_modified(False)
