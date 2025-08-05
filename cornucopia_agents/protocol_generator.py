from agents import Agent, function_tool, ModelSettings
from utils.fixed_header import get_fixed_header
import re
from agents import Agent, function_tool, ModelSettings
import re

@function_tool
def generate_protocol_body(clean_prompt: str) -> str:
    import re

    # Defaults
    sample = "sample"
    diluent = "diluent"
    sample_idx = None
    diluent_idx = None
    num_steps = 5
    mix_before_plate = False

    # Normalize prompt for matching
    prompt = clean_prompt.lower()
    prompt_clean = re.sub(r"[^\w\s]", "", prompt)

    # --- SMART MATCHING LOGIC FOR SAMPLE AND DILUENT POSITIONS ---

    # Helper for extracting well/column numbers
    def extract_idx(pattern, text):
        match = re.search(pattern, text)
        if match:
            idx = int(match.group(1))
            # Clamp to 0-11 (12-well trough)
            return max(0, min(idx - 1, 11))
        return None

    # Sample position: look for "sample is in column/well N" or aliases
    sample_idx = extract_idx(r"sample.*(?:column|well)\s*(\d+)", prompt_clean)
    if sample_idx is None:
        # Aliases for last/rightmost
        if re.search(r"sample.*(last|rightmost)", prompt_clean):
            sample_idx = 11
        # Aliases for first/leftmost
        elif re.search(r"sample.*(first|leftmost)", prompt_clean):
            sample_idx = 0

    # Diluent position: look for "diluent/water is in column/well N" or aliases
    diluent_idx = extract_idx(r"(diluent|water).*(?:column|well)\s*(\d+)", prompt_clean)
    if diluent_idx is None:
        if re.search(r"(diluent|water).*(first|leftmost)", prompt_clean):
            diluent_idx = 0
        elif re.search(r"(diluent|water).*(last|rightmost)", prompt_clean):
            diluent_idx = 11

    # Fallbacks if nothing matched
    if sample_idx is None:
        sample_idx = 1  # Default: trough.wells()[1]
    if diluent_idx is None:
        diluent_idx = 0  # Default: trough.wells()[0]

    # Debug prints
    print("CLEAN PROMPT:", prompt_clean)
    print("sample_idx after matching:", sample_idx)
    print("diluent_idx after matching:", diluent_idx)

    # --- Parse other parameters as before ---
    step_match = re.search(r"(\d+)\s*step", prompt_clean)
    if step_match:
        num_steps = int(step_match.group(1))

    if "mix" in prompt_clean and "sample" in prompt_clean and "before" in prompt_clean and "plate" in prompt_clean:
        mix_before_plate = True

    # --- HEADER + FIXED BLOCKS ---
    header = f"""# sample: '{sample}', diluent: '{diluent}', parsed sample_well: {sample_idx}, diluent_well: {diluent_idx}, num_steps: {num_steps}, mix_before_plate: {mix_before_plate}
pipette = protocol.load_instrument("flex_8channel_1000", "right")
tiprack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "A1")
plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D2")
trough = protocol.load_labware("nest_12_reservoir_15ml", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

{diluent} = trough.wells()[{diluent_idx}]
{sample} = trough.wells()[{sample_idx}]
"""

    # Optional mix
    mix_block = f"""
# Mix sample before adding to plate
pipette.pick_up_tip()
pipette.mix(3, 100, {sample})
pipette.drop_tip()
""" if mix_before_plate else ""

    # Diluent fill
    diluent_block = f"""
# Add diluent to wells A2–A{num_steps+1}
for well in plate.rows()[0][1:{num_steps+1}]:
    pipette.pick_up_tip()
    pipette.aspirate(100, {diluent})
    pipette.dispense(100, well)
    pipette.drop_tip()
"""

    # Add sample to A1
    sample_block = f"""
# Add sample to first well A1
pipette.pick_up_tip()
pipette.aspirate(100, {sample})
pipette.dispense(100, plate.rows()[0][0])
pipette.drop_tip()
"""

    # Serial dilution loop
    dilution_block = f"""
# Serial dilution across A1 to A{num_steps+1}
for i in range({num_steps}):
    source = plate.rows()[0][i]
    dest = plate.rows()[0][i+1]
    pipette.pick_up_tip()
    pipette.aspirate(100, source)
    pipette.dispense(100, dest)
    pipette.mix(3, 100, dest)
    pipette.drop_tip()
"""

    return header + mix_block + diluent_block + sample_block + dilution_block

ProtocolGeneratorAgent = Agent(
    name="ProtocolGeneratorAgent",
    instructions=(
        "You generate only the Python code inside run(protocol): based on clean_prompt. "
        "You must use the tool generate_protocol_body. Return only raw Python code — no explanation. "
        "Use the provided fixed header and ensure the code is syntactically correct. "
        "Please pay attention to the sample and diluent wells, and ensure the protocol is valid. "
        "Change the sample and diluent wells as needed based on the users request. "
        "If the prompt specifies a well position or name, use it. Otherwise, use a reasonable default. "
    ),
    tools=[generate_protocol_body],
    output_type=str,
    model_settings=ModelSettings(temperature=0),
    tool_use_behavior="stop_on_first_tool"
)
