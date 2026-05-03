from constants import Endpoints, AREA_CODE, HEADERS, TIMEOUT, EXPIRE
from abstract import Messages, Assistant, Think, Query, Response
from requests import Session, RequestException, Response as R
from encrypt import Hasher, Roam, encrypt, time
from json import dumps, loads


class Token:
    def __init__(self, session: Session, token: str):
        self.session = session
        self._token = token
        self.cache = ("", 0)

    def get(self) -> str:
        tok, exp = self.cache
        if tok and exp > time():
            return tok
        response = self.session.get(
            Endpoints.CURRENT,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=TIMEOUT,
        )
        tok = Result(response, self).data["token"]
        self.cache = (tok, time() + EXPIRE)
        return tok

    def __eq__(self, token: str):
        return self._token == token


class Tokener(list):
    def __init__(self):
        super().__init__()
        self.session = Session()
        self.session.headers.update(HEADERS)

    def new(self, token: str):
        tok = Token(self.session, token)
        self.append(tok)
        return tok


class Result:
    def __init__(self, response: R, token: Token | None = None):
        assert response.status_code == 200
        self.result = response.json()
        code = self.result["code"]
        if code == 40003 and token in tokener:
            tokener.remove(token)
        assert code == 0, self.result["msg"]

    @property
    def data(self) -> dict:
        return self.result["data"]["biz_data"]


class Handler:
    def __init__(self, token: Token):
        self._token = token

    def __call__(self, response: R):
        return Result(response, self._token)

    @property
    def token(self):
        return self._token.get()


class Client:

    def __init__(self, account: str):
        self.session = Session()
        self.session.headers.update(HEADERS)
        self.account = account
        self.token = None

    def login(self, password: str):
        for _ in range(3):
            for approach in ("mobile", "email"):
                try:
                    response = self.session.post(
                        Endpoints.LOGIN,
                        json={
                            approach: self.account,
                            "password": password,
                            "area_code": AREA_CODE,
                            "device_id": Roam.device(),
                            "os": "web",
                        },
                        headers={"Content-Type": "application/json"},
                        timeout=TIMEOUT,
                    )
                    self.token = tokener.new(Result(response).data["user"]["token"])
                    return
                except (RequestException, TypeError, KeyError):
                    pass
        raise Exception("Login failed")

    def new(self):
        return Tunnel(self.session, Handler(self.token))


tokener = Tokener()
hasher = Hasher()


class Guard:
    def __init__(self, session: Session, handler: Handler):
        self.handler = handler
        self.session = session

    def __enter__(self):
        response = self.session.post(
            Endpoints.CREATE_SESSION,
            headers={"Authorization": f"Bearer {self.handler.token}"},
            timeout=TIMEOUT,
        )
        self.id = self.handler(response).data["chat_session"]["id"]
        return self

    def __exit__(self, *_):
        response = self.session.post(
            Endpoints.DELETE_SESSION,
            json={"chat_session_id": self.id},
            headers={
                "Authorization": f"Bearer {self.handler.token}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        self.handler(response)


class Manager(Messages):
    def __init__(self):
        super().__init__()
        self.tunnels: list[Tunnel] = []
        self.current = 0
        self.model = "default"
        self.thinking = False
        self.search = False

    def bind(self, client: Client):
        self.tunnels.append(client.new())

    def send(self):
        for _ in range(len(self.tunnels)):
            try:
                return self.tunnels[self.current].send(self)
            finally:
                self.current = (self.current + 1) % len(self.tunnels)
        raise Exception("Completion failed")


class Tunnel:
    def __init__(self, session: Session, handler: Handler):
        self.handler = handler
        self.session = session
        self.cached: dict[int, dict] = {}

    def challenge(self, endpoint: str):
        response = self.session.post(
            Endpoints.CHALLENGE,
            json={"target_path": endpoint},
            headers={
                "Authorization": f"Bearer {self.handler.token}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        data = self.handler(response).data["challenge"]
        assert data["algorithm"] == "DeepSeekHashV1"
        prefix = f"{data['salt']}_{data['expire_at']}_"
        answer = hasher.hash(data["challenge"], prefix, data["difficulty"])
        result = {"answer": answer, "target_path": endpoint}
        result.update(data)
        return encrypt(dumps(result))

    def send(
        self,
        manager: Manager,
        file_ids: list = [],
    ):
        with Guard(self.session, self.handler) as g:
            response = self.session.post(
                Endpoints.COMPLETION,
                json={
                    "chat_session_id": g.id,
                    "parent_message_id": None,
                    "model_type": manager.model,
                    "prompt": str(manager),
                    "ref_file_ids": file_ids,
                    "thinking_enabled": manager.thinking,
                    "search_enabled": manager.search,
                    "preempt": False,
                },
                headers={
                    "Authorization": f"Bearer {self.handler.token}",
                    "Content-Type": "application/json",
                    "Cookie": Roam.cookie(),
                    "X-Ds-Pow-Response": self.challenge(Endpoints.COMPLETION_EP),
                },
                timeout=TIMEOUT,
                stream=True,
            )
            assert response.status_code == 200
            message = manager.new()
            self.cached.clear()
            for chunk in response.iter_lines(chunk_size=None, decode_unicode=True):
                chunk = str(chunk).strip()
                if chunk.startswith("data: "):
                    data = loads(chunk[6:])
                    self.parse(message, data)
            message.stop()
            return message

    def parse(self, message: Assistant, data: dict):
        if data:
            v = data.get("v")
            if isinstance(v, list):
                for item in v:
                    self.parse(message, item)
            elif isinstance(v, dict):
                self.parse(message, v["response"]["fragments"][0])
            elif isinstance(v, str):
                p = data.get("p")
                if not p or "/content" in p:
                    message.update(v)
            elif "type" in data:
                t = data["type"]
                content = data.get("content")
                if t == "TOOL_OPEN":
                    id = data["id"]
                    result = self.cached.get(id)
                    if result:
                        link = f"[{result.get('title', '')}]({result.get('url', '')})"
                        message.link(id, link)
                    elif "result" in data:
                        self.cached[id] = data["result"]
                elif t == "TOOL_SEARCH" and "queries" in data:
                    message.append(Query(data["queries"]))
                elif t == "THINK" and content:
                    message.append(Think(content))
                elif t == "RESPONSE" and content:
                    message.append(Response(content))
