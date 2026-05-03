from abstract import Container, Content, User, System, Think, Response, Search
from widgets import Context, Stack
from client import Client, Manager
from threading import Thread
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

context = Context(main)
context.grid(row=0, column=2, sticky=tk.NSEW)
scrollbar = tk.Scrollbar(main, command=context.yview)
context.config(yscrollcommand=scrollbar.set)
scrollbar.grid(row=0, column=3, sticky=tk.NS)

stack = Stack(main, context)
stack.grid(row=0, column=1, padx=10, sticky=tk.NSEW)

messages = Stack(main, stack)
messages.grid(row=0, column=0, sticky=tk.NSEW)
messages.default = {User.type: lambda: User(""), System.type: lambda: System("")}

# messages.append(Container([Content("Hello, world!"), Content("...")]))
# messages.append(System("You are a helpful assistant."))
# messages.append(User("Hello, world!"))
# messages.append(
#     Container([Think("..."), Search(["A", "B", "C"]), Response("Hello, world!")])
# )

root.mainloop()
