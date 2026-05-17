from tomlkit import load

CONFIG = load(open("widgets/config.toml", encoding="utf-8")).unwrap()


class UI:
    SIZE = CONFIG["SIZE"]
    THEME = CONFIG["THEME"]
    SCALE = CONFIG["SCALE"]
    TITLE = CONFIG["TITLE"]

    class Button:
        SEND = CONFIG["BUTTON"]["SEND"]
        STOP = CONFIG["BUTTON"]["STOP"]

    class Menu:
        DELETE = CONFIG["MENU"]["DELETE"]
        DRAFT = CONFIG["MENU"]["DRAFT"]

    class Default:
        SYSTEM = CONFIG["DEFAULT"]["SYSTEM"]
        USER = CONFIG["DEFAULT"]["USER"]
