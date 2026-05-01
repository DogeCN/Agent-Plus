from constants import Endpoints, AREA_CODE, HEADERS, TIMEOUT, EXPIRE
from encrypt import Hasher, Roam, encrypt, time
from requests import Session, Response as R
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
    def __init__(self, response: R, token: Token):
        assert response.status_code == 200
        self.result = response.json()
        code = self.result["code"]
        if code == 40003:
            tokener.remove(token)
        assert code == 0, self.result["msg"]

    @property
    def data(self) -> dict:
        return self.result["data"]["biz_data"]


class Handler:
    def __init__(self, token: Token):
        self._token = token

    def __call__(self, response: R):
        return Result(response, self.token)

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
                    self.token = tokener.new(
                        Result(response, self.token).data["user"]["token"]
                    )
                    return
                except:
                    pass
        raise Exception("Login failed")

    def new(self):
        return Tunnel(self.session, Handler(self.token))


tokener = Tokener()
hasher = Hasher()


def probe(data: dict, bound: tuple):
    if bound:
        key = bound[0]
        if key is None:
            results = []
            for v in list(data):
                res = probe(v, bound[1:])
                if res is not None:
                    results.append(res)
            return results
        try:
            return probe(data[key], bound[1:])
        except (KeyError, IndexError, TypeError):
            return
    return data


def multiprobe(data: dict, *bounds: tuple):
    for i, bound in enumerate(bounds):
        result = probe(data, bound)
        if result is not None:
            return i, result


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


class Container:
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content.strip()


class System(Container):
    def __str__(self):
        return "<｜System｜>" + super().__str__()


class User(System):
    def __str__(self):
        return "<｜User｜>" + Container.__str__(self)


class Think(Container):
    def update(self, chunk: str):
        self.content += chunk


class Search:
    def __init__(self, queries: list[str]):
        self.queries = queries

    def __str__(self):
        return "\n".join(self.queries)


class Response(Think):
    actions = None


type Part = Think | Search | Response


class Assistant(list[Part]):
    actions = None

    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def update(self, chunk: str):
        self[-1].update(chunk)

    def __str__(self):
        responses = [str(part) for part in self if isinstance(part, Response)]
        return "<｜Assistant｜>" + "\n".join(responses) + "<｜end▁of▁sentence｜>"


type Message = System | User | Assistant


class Manager(list[Message]):
    mapping: dict[str, type[Part]] = ...
    model = "default"
    thinking = False
    search = False

    def __init__(self):
        self.tunnels: list[Tunnel] = []
        self.current = 0

    def send(self):
        for _ in range(len(self.tunnels)):
            tunnel = self.tunnels[self.current]
            try:
                self.append(Assistant("\n".join(map(str, self))))
                tunnel.send(self)
                return
            finally:
                self.current = (self.current + 1) % len(self.tunnels)
        raise Exception("Completion failed")


class Tunnel:
    def __init__(self, session: Session, handler: Handler):
        self.handler = handler
        self.session = session

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
            message: Assistant = manager[-1]
            response = self.session.post(
                Endpoints.COMPLETION,
                json={
                    "chat_session_id": g.id,
                    "parent_message_id": None,
                    "model_type": manager.model,
                    "prompt": message.prompt,
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
            for chunk in response.iter_lines(chunk_size=None, decode_unicode=True):
                chunk = str(chunk).strip()
                if " " in chunk:
                    if chunk.startswith("data: "):
                        data = loads(chunk[6:])
                        if "v" in data:
                            data = data["v"]
                            if isinstance(data, list | dict):
                                res = multiprobe(
                                    data,
                                    (0, "v", 0, "type"),
                                    ("response", "fragments", 0, "type"),
                                    (0, "type"),
                                    (1, "v", 0, "type"),
                                )
                                if res:
                                    i, t = res
                                    if i == 0:
                                        c = data[0]["v"]
                                        if t in manager.mapping:
                                            part = manager.mapping[t](c[0]["content"])
                                        elif t == "TOOL_SEARCH":
                                            q = [v["queries"][0]["query"] for v in c]
                                            part = Search(q)
                                    elif i == 1:
                                        c = data["response"]["fragments"][0]["content"]
                                        if t in manager.mapping:
                                            part = manager.mapping[t](c)
                                    elif i == 2 and t == "RESPONSE":
                                        part = manager.mapping[t](c)
                                    elif i == 3:
                                        print(t)
                                    message.append(part)
                            elif isinstance(data, str) and data != "FINISHED":
                                message.update(data)
