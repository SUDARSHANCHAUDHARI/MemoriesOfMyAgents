import time
import random
import string


def _suffix(length: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def session_id() -> str:
    return f"ses_{int(time.time() * 1000)}_{_suffix(6)}"


def memory_id() -> str:
    return f"mem_{int(time.time() * 1000)}_{_suffix(6)}"


def observation_id() -> str:
    return f"obs_{int(time.time() * 1000)}_{_suffix(6)}"
