from tunnel import Tunnel, Mark
from concurrent.futures import ThreadPoolExecutor
from random import choice
import subprocess
import time
import sys
import os
import re


class Message:
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return f"<｜{type(self).__name__}｜>{self.content}"


class User(Message): ...


class Block:

    def __init__(self, mark: Mark):
        self.mark = mark
        self.content = ""

    def update(self, chunk: str):
        self.content += chunk

    def __str__(self):
        return self.content


class Code:
    mark = Mark.CODE

    def __init__(self, redirect: Mark):
        self.redirect = redirect
        self.content = self.output = ""
        self.running = False

    def update(self, chunk: str):
        if chunk.startswith("```"):
            return self.redirect
        else:
            self.content += chunk

    def __str__(self):
        return f"```{self.content}```\n```output\n{self.output}```\n\n"

    def _exec(self, code: str, language: str, timeout: int | None):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "errors": "replace",
            "bufsize": 1,
            "env": env,
        }
        if language == "python":
            process = subprocess.Popen(
                [sys.executable, "-u", "-"], encoding="utf-8", **kwargs
            )
        elif language == "powershell":
            process = subprocess.Popen(
                ["pwsh", "-NoProfile", "-Command", "-"], encoding="utf-16-le", **kwargs
            )
        else:
            return
        start = time.time()
        process.stdin.write(code)
        process.stdin.close()
        for line in process.stdout:
            self.output += line
        process.wait(timeout)
        self.output += f"[Process terminated in {time.time() - start} seconds]\n"
        return True

    def exec(self):
        if self.running:
            return
        self.running = True
        if "\n" in self.content:
            meta, code = self.content.split("\n", 1)
            matched = re.search(r"(\w+)\s+exec\((?:timeout=(\d+))?\)", meta)
            if matched:
                language = matched.group(1)
                timeout = matched.group(2)
                if timeout:
                    timeout = eval(timeout)
                return self._exec(code, language, timeout)
        self.running = False


class Assistant(Message):

    def __init__(self):
        self.parts: list[Block | Code] = []
        self.pool = ThreadPoolExecutor()
        self.cycle = False

    def update(self, chunk: Mark | str):
        if isinstance(chunk, Mark):
            self.parts.append(Block(chunk))
        else:
            current = self.parts[-1]
            if chunk == "```" and current.mark == Mark.RESPONSE:
                # Parse Code in Response Only
                self.parts.append(Code(Mark.RESPONSE))
            else:
                redirect = current.update(chunk)
                if redirect:
                    self.pool.submit(self.exec, current)
                    self.parts.append(Block(redirect))

    def exec(self, code: Code):
        if code.exec():
            self.cycle = True

    def __str__(self) -> str:
        prepared = ""
        for part in self.parts:
            if part.mark in (Mark.RESPONSE, Mark.CODE):
                prepared += str(part) + "\n"
        return f"<｜Assistant｜>{prepared}"


class History(list[Message]):
    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def __str__(self):
        prepared = "\n".join(map(str, self))
        return f"<｜System｜>{self.prompt}\n{prepared}"


class Manager(list[Tunnel]):
    model = "default"
    thinking = False
    search = False

    def __init__(self, history: History):
        self.history = history

    def send(self, user: User):
        self.history.append(user)
        while True:
            assistant = Assistant()
            for chunk in choice(self).send(
                str(self.history), self.model, self.thinking, self.search
            ):
                assistant.update(chunk)
                yield assistant.parts
            self.history.append(assistant)
            if assistant.cycle:
                assistant.pool.shutdown()
                self.history.append(User("[Codes Executed]"))
                yield
            else:
                break
