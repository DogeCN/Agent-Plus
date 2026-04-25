AREA_CODE = "+86"
WASM = "runtime.wasm"
EXPIRE = 3600
TIMEOUT = 3

HOST = "https://chat.deepseek.com"


class Endpoints:
    @staticmethod
    def endpoint(path: str) -> str:
        return f"{HOST}/api/v0/{path}"

    CURRENT = endpoint("users/current")
    LOGIN = endpoint("users/login")
    COMPLETION = endpoint("chat/completion")
    CREATE_SESSION = endpoint("chat_session/create")
    DELETE_SESSION = endpoint("chat_session/delete")
    CHALLENGE = endpoint("chat/create_pow_challenge")
    COMPLETION_EP = "/api/v0/chat/completion"


HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Origin": HOST,
    "Pragma": "no-cache",
    "Priority": "u=1, i",
    "Referer": f"{HOST}/",
    "Sec-Ch-Ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    "X-App-Version": "20241129.1",
    "X-Client-Locale": "zh_CN",
    "X-Client-Platform": "web",
    "X-Client-Version": "1.8.0",
}
