from tkinter import Tk
from tkinter.font import Font
from ctypes import windll

try:
    windll.shcore.SetProcessDpiAwareness(2)
except:
    windll.shcore.SetProcessDpiAwareness()


class Window(Tk):
    type Size = tuple[float, float]

    def __init__(self, master, title: str, size: Size):
        super().__init__(master)
        self.title(title)
        sc_width = self.winfo_screenwidth()
        sc_height = self.winfo_screenheight()
        width = int(sc_width * size[0])
        height = int(sc_height * size[1])
        self.geometry(f"{width}x{height}+{(sc_width-width)//2}+{(sc_height-height)//2}")
        self.scale = self.winfo_fpixels("1i") / 72
        self.tk.call("tk", "scaling", self.scale)

    def grid(self, row: tuple[int], column: tuple[int]):
        for i, r in enumerate(row):
            self.rowconfigure(i, weight=r)
        for i, c in enumerate(column):
            self.columnconfigure(i, weight=c)

    def font(self, font: Font):
        self.option_add("*Font", font)
