from concurrent.futures import ThreadPoolExecutor
from widgets import Context, Stack, Drafts, Toolbar
from abstract import User, System, Parent
from client import Client, Manager
from config import UI, accounts
from tkinter import ttk, font
from ctypes import windll
import tkinter as tk

try:
    windll.shcore.SetProcessDpiAwareness(2)
except:
    windll.shcore.SetProcessDpiAwareness()
root = tk.Tk()
root.title(UI.TITLE)
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
width = int(screen_width * UI.SIZE[0])
height = int(screen_height * UI.SIZE[1])
root.geometry(f"{width}x{height}+{(screen_width-width)//2}+{(screen_height-height)//2}")
scale = root.winfo_fpixels("1i") / 72
root.tk.call("tk", "scaling", scale)
tkfont = font.nametofont("TkDefaultFont")
tkfont.configure(size=int(scale * UI.SCALE))
root.option_add("*Font", tkfont)
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
style = ttk.Style()
style.theme_use(UI.THEME)

main = tk.Frame(root)
main.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)
main.grid_rowconfigure(0, weight=20)
main.grid_rowconfigure(1, weight=1)
main.grid_rowconfigure(2, weight=1)
main.grid_columnconfigure(0, weight=1)
main.grid_columnconfigure(1, weight=2)

context = Context(main)
scrollbar = tk.Scrollbar(main, command=context.yview)
context.config(yscrollcommand=scrollbar.set)
context.grid(row=0, column=1, rowspan=3, sticky=tk.NSEW)
scrollbar.grid(row=0, column=2, rowspan=3, sticky=tk.NS)

detail = Stack(main, context)
detail.grid(row=1, column=0, padx=10, pady=10, sticky=tk.NSEW)

stack = Stack(main, detail)
stack.grid(row=0, column=0, padx=10, sticky=tk.NSEW)

draft = Drafts(stack)
draft.append(User, UI.Default.USER)
draft.append(System, UI.Default.SYSTEM)


class Messages(Manager):
    def __init__(self, viewer: Parent):
        super().__init__()
        viewer.view(self)
        self.pool = ThreadPoolExecutor()
        self.pool.submit(self.load)

    def load(self):
        for account in accounts:
            client = Client(account["account"])
            client.login(account["password"])
            self.bind(client)

    def send(self):
        self.pool.submit(super().send)


messages = Messages(stack)

toolbar = Toolbar(main)
toolbar.grid(row=0, column=3, padx=10, pady=10, sticky=tk.NSEW)

send = ttk.Button(main, text=UI.Button.SEND, command=messages.send)
send.grid(row=2, column=0, padx=10, pady=10, sticky=tk.NSEW)

stop = ttk.Button(main, text=UI.Button.STOP)
stop.grid(row=2, column=1, padx=10, pady=10, sticky=tk.NSEW)

root.mainloop()
