from deepseek.abstract import User, System, DeepseekMessages
from tkinter import ttk, font

from .stack import Stack, Edit
from .window import Window
from .field import Field
from .config import UI

root = Window(None, UI.TITLE, UI.SIZE)

tkfont = font.nametofont("TkDefaultFont")
tkfont.configure(size=int(root.scale * UI.SCALE))
root.font(tkfont)
style = ttk.Style()
style.theme_use(UI.THEME)

root.grid((20, 1), (1, 2))

field = Field(root)
field.grid((0, 2), (1, 1))

detail = Stack(root, field)
detail.grid((1, 1), (0, 1))

stack = Stack(root, detail)
stack.grid((0, 1), (0, 1))

stack.host(DeepseekMessages())

draft = Edit(stack)
draft.append(User, UI.Default.USER)
draft.append(System, UI.Default.SYSTEM)
