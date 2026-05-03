import tomllib

config = tomllib.load(open("config.toml"))
accounts = [(account["Account"], account["Password"]) for account in config["Accounts"]]

SIZE = config["SIZE"]
TITLE = config["TITLE"]
THEME = config["THEME"]
SCALE = config["SCALE"]

AREA_CODE = config["AREA_CODE"]
WASM = config["WASM"]
EXPIRE = config["EXPIRE"]
TIMEOUT = config["TIMEOUT"]


HOST = config["HOST"]
HEADERS = config["HEADERS"]
EP_ROOT = config["Endpoints"]


class Endpoints:
    CURRENT = EP_ROOT["CURRENT"]
    LOGIN = EP_ROOT["LOGIN"]
    COMPLETION = EP_ROOT["COMPLETION"]
    CREATE_SESSION = EP_ROOT["CREATE_SESSION"]
    DELETE_SESSION = EP_ROOT["DELETE_SESSION"]
    CHALLENGE = EP_ROOT["CHALLENGE"]

    class Referer:
        COMPLETION = EP_ROOT["Referer"]["COMPLETION"]
