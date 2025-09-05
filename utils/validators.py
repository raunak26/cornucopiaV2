# utils/validators.py
import re
from typing import Dict, Optional, Tuple, List

VALID_FLEX_SLOTS = {f"{r}{c}" for r in "ABCD" for c in "123"}
LABWARE_WHITELIST = {
    "opentrons_flex_96_tiprack_1000ul",
    "nest_96_wellplate_200ul_flat",
    "nest_12_reservoir_15ml",
    "opentrons_flex_trash",
}
PIPETTE_WHITELIST = {"flex_8channel_1000", "flex_1channel_50", "flex_1channel_1000"}

RISK_KEYWORDS = [
    "pathogen", "bsL3", "bsL4", "live virus", "toxic", "carcinogen",
    "corrosive", "hydrofluoric", "cyanide", "radioactive", "select agent"
]

class ValidationError(Exception):
    pass

def structural_checks(code: str) -> None:
    # Pipette models
    for m in re.findall(r'load_instrument\("([^"]+)"', code):
        if m not in PIPETTE_WHITELIST:
            raise ValidationError(f"Unsupported pipette '{m}'")

    # Labware load names and slots
    for load_name, slot in re.findall(r'load_labware\("([^"]+)",\s*"([^"]+)"\)', code):
        if load_name not in LABWARE_WHITELIST:
            raise ValidationError(f"Unsupported labware '{load_name}'")
        if slot not in VALID_FLEX_SLOTS:
            raise ValidationError(f"Invalid slot '{slot}' for Flex")

    # Trash slot sanity (optional but nice)
    for slot in re.findall(r'load_trash_bin\("([^"]+)"\)', code):
        if slot not in VALID_FLEX_SLOTS:
            raise ValidationError(f"Invalid trash slot '{slot}'")

    # Basic volume sanity: disallow > 1000 µL on p1000_8 and < 10 µL transfers for reliability
    for vol_s in re.findall(r'(?:aspirate|dispense)\((\d+)', code):
        v = int(vol_s)
        if v > 1000:
            raise ValidationError(f"Volume {v} µL exceeds 1000 µL limit")
        if v < 5:
            raise ValidationError(f"Volume {v} µL is below safe accuracy threshold")

def _extract_clean_params(clean_prompt: str) -> Dict:
    p = clean_prompt.lower()
    out: Dict = {}
    # steps
    m = re.search(r'(\d+)\s*(?:step|dilution)s?', p)
    if m:
        out["num_steps"] = int(m.group(1))
    # plate type
    m = re.search(r'(nest_\d+_wellplate_\d+ul_[a-z]+)', p)
    if m:
        out["plate_type"] = m.group(1)
    # sample/diluent locations
    for key in ["sample", "diluent", "water"]:
        m = re.search(fr'{key}.*(?:column|well)\s*(\d+)', p)
        if m:
            out[f"{key}_well"] = int(m.group(1))
    # risk words
    out["risk_hits"] = [w for w in RISK_KEYWORDS if w in p]
    return out

def semantic_checks(code: str, clean_prompt: str) -> None:
    """Does the generated code appear to match intent from clean_prompt?"""
    want = _extract_clean_params(clean_prompt)

    # Plate type
    if "plate_type" in want:
        if want["plate_type"] not in code:
            raise ValidationError(f"Requested plate '{want['plate_type']}' not found in code")

    # Steps → count serial moves across a row (A1->A2 etc). Heuristic but effective.
    if "num_steps" in want:
        # Count transfer loop occurrences or explicit transfer chain
        loop_m = re.search(r'for i in range\((\d+)\):', code)
        if loop_m:
            got_steps = int(loop_m.group(1))
        else:
            # Count sequential transfer pairs A1->A2, A2->A3, ...
            pairs = re.findall(r'rows\(\)\[0\]\[(\d+)\].*rows\(\)\[0\]\[(\d+)\]', code, re.S)
            got_steps = len(pairs)
        if got_steps and got_steps != want["num_steps"]:
            raise ValidationError(f"Expected {want['num_steps']} dilution steps but code shows {got_steps}")

    # Wells for sample/diluent
    for key in ["sample", "diluent", "water"]:
        if f"{key}_well" in want:
            idx = want[f"{key}_well"] - 1  # code uses 0-based index in trough.wells()[i]
            if f"= trough.wells()[{idx}]" not in code and f'wells_by_name()["A{want[f"{key}_well"]}"]' not in code:
                raise ValidationError(f"Requested {key} well {want[f'{key}_well']} not located in generated code")

    # High risk content
    if want.get("risk_hits"):
        raise ValidationError(f"High-risk materials mentioned: {', '.join(want['risk_hits'])}")

def policy_checks(clean_prompt: str) -> None:
    """Enforce basic lab policy: disallow BSL-3/4, select agents, corrosives, etc."""
    p = clean_prompt.lower()
    hits = [w for w in RISK_KEYWORDS if w in p]
    if hits:
        raise ValidationError(f"Blocked by policy. Found high-risk terms: {', '.join(hits)}")