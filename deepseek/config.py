from tomlkit import load, dump

config = load(open("deepseek/config.toml", encoding="utf-8"))
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


def save():
    dump(config, open("config.toml", "w", encoding="utf-8"))
