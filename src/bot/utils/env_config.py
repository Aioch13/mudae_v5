import os

ENV_PATH = ".env"

def read_env():
    """Read all key=value pairs from .env into a dict."""
    if not os.path.exists(ENV_PATH):
        return {}
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if "=" in line and not line.strip().startswith("#")]
    env = {}
    for line in lines:
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env

def write_env(key, value):
    """Update or add a key=value in .env persistently."""
    env = read_env()
    env[key] = str(value)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    print(f"[💾] Saved {key}={value} to .env")
