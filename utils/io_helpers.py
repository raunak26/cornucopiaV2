import os

def save_protocol(code: str, filename: str = None, outdir: str = "generated") -> str:
    if not filename:
        filename = "generated_protocol.py"
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    path = os.path.join(outdir, filename)
    with open(path, "w") as f:
        f.write(code)
    return path

def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)
