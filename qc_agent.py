import subprocess

def simulate_protocol(path: str) -> tuple[str, str]:
    result = subprocess.run(
        ["opentrons_simulate", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.stdout, result.stderr

def extract_missing_params(stderr: str) -> list[str]:
    if "KeyError" in stderr:
        return ["missing dictionary key"]
    if "SlotDoesNotExistError" in stderr:
        return ["invalid or missing deck slot"]
    if "No module named" in stderr:
        return ["missing import or pip module"]
    if "TypeError" in stderr and "missing" in stderr:
        return ["missing function argument"]
    return ["unrecognized error - manual inspection needed"]
