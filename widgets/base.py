from tkinter import Widget, NSEW


class Base(Widget):
    def grid(
        self,
        row: tuple[int, int],
        column: tuple[int, int],
        padx: int = 10,
        pady: int = 10,
        sticky: str = NSEW,
    ):
        super().grid(
            row=row[0],
            column=column[0],
            rowspan=row[1],
            columnspan=column[1],
            padx=padx,
            pady=pady,
            sticky=sticky,
        )
