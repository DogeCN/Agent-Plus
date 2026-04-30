from subprocess import Popen, TimeoutExpired, PIPE, STDOUT
from threading import Thread
from time import time

template = ". D:\\Agent\\session.ps1; Restore-Session; try { %s } catch { $_ | Write-Error }; Save-Session\n\n"


def format(secs: float) -> str:
    units = [
        ("d", 24),
        ("h", 60),
        ("min", 60),
        ("s", 1000),
        ("ms", 1000),
        ("μs", 1000),
        ("ns", None),
    ]
    idx = 3
    while idx > 0 and secs >= units[idx - 1][1]:
        secs /= units[idx - 1][1]
        idx -= 1
    while idx < len(units) - 1 and secs < 1:
        secs *= units[idx][1]
        idx += 1
    return f"{secs:.2f} {units[idx][0]}"


def pwsh(code: str, timeout: int):
    process = Popen(
        [
            "pwsh",
            "-NoProfile",
            "-NoLogo",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "-",
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=STDOUT,
    )
    process.stdin.write((template % code).encode())
    process.stdin.close()

    hint = ""

    def wait():
        nonlocal hint
        try:
            start = time()
            xcode = process.wait(timeout=timeout)
            spent = format(time() - start)
            hint = f"Process finished with exit code {xcode} and in {spent}"
        except TimeoutExpired:
            process.kill()
            hint = f"Process timed out"

    handler = Thread(target=wait, daemon=True)
    handler.start()
    for line in process.stdout:
        yield line.decode()

    handler.join()
    yield f"\n[{hint}]\n"
