from wasmtime import Engine, Store, Linker, Module, Instance
from constants import WASM
from base64 import b64encode
from hashlib import sha256
from struct import unpack
from uuid import uuid4
from time import time
import ctypes


def encrypt(text: str) -> str:
    return b64encode(text.encode()).decode()


class Roam:

    @staticmethod
    def device():
        raw = f"{uuid4()}{time()}DeepSeekDevice"
        return b64encode(sha256(raw.encode()).digest()).decode()

    @staticmethod
    def cookie():
        timestamp = time()
        id = uuid4().hex
        cookie_parts = [
            f"intercom-HWWAFSESTIME={timestamp}",
            f"HWWAFSESID={uuid4().hex[:18]}",
            f"Hm_lvt_{id}={timestamp},{timestamp},{timestamp}",
            f"Hm_lpvt_{id}={timestamp}",
            f"_frid={uuid4().hex}",
            f"_fr_ssid={uuid4().hex}",
            f"_fr_pvid={uuid4().hex}",
        ]
        return "; ".join(cookie_parts)


class Assembly:
    def __init__(self, instance: Instance, store: Store):
        self.store = store
        self.exports = instance.exports(store)
        self.addr = ctypes.cast(
            self.exports["memory"].data_ptr(self.store), ctypes.c_void_p
        ).value

    def write(self, offset: int, data: bytes):
        ctypes.memmove(self.addr + offset, data, len(data))

    def read(self, offset: int, size: int) -> bytes:
        return ctypes.string_at(self.addr + offset, size)

    def write_string(self, text: str) -> tuple[int, int]:
        data = text.encode()
        length = len(data)
        ptr_val = self.exports["__wbindgen_export_0"](self.store, length, 1)
        ptr = int(getattr(ptr_val, "value") if hasattr(ptr_val, "value") else ptr_val)
        self.write(ptr, data)
        return ptr, length

    def add(self, value: int):
        return self.exports["__wbindgen_add_to_stack_pointer"](self.store, value)

    @property
    def solve(self):
        return self.exports["wasm_solve"]


class Hasher:
    def __init__(self):
        self.engine = Engine()
        self.store = Store(self.engine)
        linker = Linker(self.engine)
        linker.define_wasi()
        module = Module(self.engine, open(WASM, "rb").read())
        instance = linker.instantiate(self.store, module)
        self.assembly = Assembly(instance, self.store)

    def hash(self, challenge: str, prefix: str, difficulty: int) -> str:
        retptr = self.assembly.add(-16)
        ptr_challenge, len_challenge = self.assembly.write_string(challenge)
        ptr_prefix, len_prefix = self.assembly.write_string(prefix)
        self.assembly.solve(
            self.store,
            retptr,
            ptr_challenge,
            len_challenge,
            ptr_prefix,
            len_prefix,
            float(difficulty),
        )
        try:
            status = self.assembly.read(retptr, 4)
            assert unpack("<i", status)[0] != 0
            value = self.assembly.read(retptr + 8, 8)
            assert len(value) == 8
            return int(unpack("<d", value)[0])
        finally:
            self.assembly.add(16)
