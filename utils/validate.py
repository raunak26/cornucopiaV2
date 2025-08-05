import re

def check_missing_params(user_prompt: str):
    missing = []
    if not re.search(r"\b(\d+)\s*(samples?|wells?|columns?)\b", user_prompt, re.I):
        missing.append("number of samples")
    if not re.search(r"\b(\d+)\s*(uL|ul|microliters?)\b", user_prompt, re.I):
        missing.append("volume in uL")
    if not re.search(r"incubat\w*\s*(for)?\s*(\d+)\s*(min|minutes?)", user_prompt, re.I):
        missing.append("incubation time")
    return missing

def is_valid(user_prompt: str):
    has_samples = bool(re.search(r"\b(\d+)\s*(samples?|wells?|columns?)\b", user_prompt, re.I))
    has_volume = bool(re.search(r"\b(\d+)\s*(uL|ul|microliters?)\b", user_prompt, re.I))
    has_incubation = bool(re.search(r"incubat\w*\s*(for)?\s*(\d+)\s*(min|minutes?)\b", user_prompt, re.I))
    return has_samples and has_volume and has_incubation
