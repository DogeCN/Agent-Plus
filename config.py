from tomlkit import load, dump

config = load(open("config.toml", encoding="utf-8"))
accounts = config["accounts"]
model = config["model"]

CONFIG = config.unwrap()

AREA_CODE = CONFIG["AREA_CODE"]
WASM = CONFIG["WASM"]
EXPIRE = CONFIG["EXPIRE"]
TIMEOUT = CONFIG["TIMEOUT"]
MODELS = CONFIG["MODELS"]

HEADERS = CONFIG["HEADERS"]
EP_ROOT = CONFIG["Endpoints"]
UI_ROOT = CONFIG["UI"]


class Endpoints:
    def get(key: str):
        return f"{EP_ROOT["ROOT"]}/{EP_ROOT[key]}"

    CURRENT = get("CURRENT")
    LOGIN = get("LOGIN")
    COMPLETION = get("COMPLETION")
    CREATE_SESSION = get("CREATE_SESSION")
    DELETE_SESSION = get("DELETE_SESSION")
    CHALLENGE = get("CHALLENGE")

    class Referer:
        COMPLETION = EP_ROOT["Referer"]["COMPLETION"]


class UI:
    SIZE = UI_ROOT["SIZE"]
    THEME = UI_ROOT["THEME"]
    SCALE = UI_ROOT["SCALE"]
    TITLE = UI_ROOT["TITLE"]

    class Button:
        SEND = UI_ROOT["BUTTON"]["SEND"]
        STOP = UI_ROOT["BUTTON"]["STOP"]

    class Menu:
        DELETE = UI_ROOT["MENU"]["DELETE"]
        DRAFT = UI_ROOT["MENU"]["DRAFT"]

    class Default:
        SYSTEM = UI_ROOT["DEFAULT"]["SYSTEM"]
        USER = UI_ROOT["DEFAULT"]["USER"]


def save():
    dump(config, open("config.toml", "w", encoding="utf-8"))
