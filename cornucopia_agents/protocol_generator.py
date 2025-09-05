from agents import Agent, function_tool, ModelSettings
from utils.fixed_header import get_fixed_header
import re
import json

@function_tool
def generate_general_protocol(clean_prompt: str) -> str:
    """
    Generates Opentrons protocol code for various types of experiments based on the clean prompt.
    Supports serial dilutions, PCR setup, plate washing, sample transfers, and more.
    """
    
    # Parse experiment type and parameters from the prompt
    experiment_info = parse_experiment_details(clean_prompt)
    
    # Generate appropriate protocol code based on experiment type
    if experiment_info["type"] == "serial_dilution":
        return generate_serial_dilution_protocol(experiment_info)
    elif experiment_info["type"] == "pcr_setup":
        return generate_pcr_setup_protocol(experiment_info)
    elif experiment_info["type"] == "plate_washing":
        return generate_plate_washing_protocol(experiment_info)
    elif experiment_info["type"] == "sample_transfer":
        return generate_sample_transfer_protocol(experiment_info)
    elif experiment_info["type"] == "cell_culture":
        return generate_cell_culture_protocol(experiment_info)
    elif experiment_info["type"] == "enzyme_assay":
        return generate_enzyme_assay_protocol(experiment_info)
    else:
        # Generic protocol for unrecognized experiments
        return generate_generic_protocol(experiment_info)

def parse_experiment_details(prompt: str) -> dict:
    """Parse experiment type and extract relevant parameters from the prompt."""
    
    prompt_lower = prompt.lower()
    
    # Initialize experiment info with defaults
    info = {
        "type": "generic",
        "num_samples": 8,
        "volume": 100,
        "pipette_type": "flex_8channel_1000",
        "pipette_mount": "right",
        "plate_type": "nest_96_wellplate_200ul_flat",
        "tip_type": "opentrons_flex_96_tiprack_1000ul",
        "source_labware": "nest_12_reservoir_15ml",
        "dilution_factor": 2,
        "num_dilutions": 5,
        "mix_after": True,
        "temperature": None,
        "incubation_time": None
    }
    
    # Determine experiment type
    if "serial dilution" in prompt_lower:
        info["type"] = "serial_dilution"
    elif any(term in prompt_lower for term in ["pcr", "amplification", "reaction mix"]):
        info["type"] = "pcr_setup"
    elif any(term in prompt_lower for term in ["wash", "washing", "rinse"]):
        info["type"] = "plate_washing"
    elif any(term in prompt_lower for term in ["transfer", "move", "aliquot"]):
        info["type"] = "sample_transfer"
    elif any(term in prompt_lower for term in ["cell", "culture", "media", "passage"]):
        info["type"] = "cell_culture"
    elif any(term in prompt_lower for term in ["enzyme", "assay", "substrate", "kinetic"]):
        info["type"] = "enzyme_assay"
    
    # Extract numerical parameters
    volume_match = re.search(r'(\d+)\s*(?:ul|µl|microliter)', prompt_lower)
    if volume_match:
        info["volume"] = int(volume_match.group(1))
    
    samples_match = re.search(r'(\d+)\s*(?:samples?|wells?)', prompt_lower)
    if samples_match:
        info["num_samples"] = int(samples_match.group(1))
    
    dilution_match = re.search(r'1:(\d+)|(\d+)x?\s*dilution', prompt_lower)
    if dilution_match:
        info["dilution_factor"] = int(dilution_match.group(1) or dilution_match.group(2))
    
    steps_match = re.search(r'(\d+)\s*(?:steps?|dilutions?)', prompt_lower)
    if steps_match:
        info["num_dilutions"] = int(steps_match.group(1))
    
    temp_match = re.search(r'(\d+)\s*(?:°c|celsius|degrees)', prompt_lower)
    if temp_match:
        info["temperature"] = int(temp_match.group(1))
    
    time_match = re.search(r'(\d+)\s*(?:min|minutes?|sec|seconds?|hours?)', prompt_lower)
    if time_match:
        info["incubation_time"] = int(time_match.group(1))
    
    # Extract pipette preferences
    if "1-channel" in prompt_lower or "single" in prompt_lower:
        info["pipette_type"] = "flex_1channel_1000"
    elif "8-channel" in prompt_lower or "multi" in prompt_lower:
        info["pipette_type"] = "flex_8channel_1000"
    
    if "50ul" in prompt_lower or "50 ul" in prompt_lower:
        info["pipette_type"] = "flex_8channel_50"
        info["tip_type"] = "opentrons_flex_96_tiprack_50ul"
    
    # Extract plate preferences
    if "pcr" in prompt_lower:
        info["plate_type"] = "nest_96_wellplate_100ul_pcr_full_skirt"
    elif "384" in prompt_lower:
        info["plate_type"] = "corning_384_wellplate_112ul_flat"
    
    return info

def generate_serial_dilution_protocol(info: dict) -> str:
    """Generate serial dilution protocol code."""
    
    # Determine if using 8-channel (row-wise) or 1-channel (well-wise)
    is_multichannel = "8channel" in info["pipette_type"]
    
    header = f"""# Serial Dilution Protocol
# Type: {info["type"]}, Samples: {info["num_samples"]}, Volume: {info["volume"]}µL
# Dilution: 1:{info["dilution_factor"]}, Steps: {info["num_dilutions"]}

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
plate = protocol.load_labware("{info["plate_type"]}", "D2")
trough = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

diluent = trough.wells()[0]
sample = trough.wells()[1]
"""

    if is_multichannel:
        protocol_body = f"""
# Add diluent to wells A2–A{info["num_dilutions"]+1} (8-channel, row-wise)
for well in plate.rows()[0][1:{info["num_dilutions"]+1}]:
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, diluent)
    pipette.dispense({info["volume"]}, well)
    pipette.drop_tip()

# Add sample to first well A1
pipette.pick_up_tip()
pipette.aspirate({info["volume"]}, sample)
pipette.dispense({info["volume"]}, plate.rows()[0][0])
pipette.drop_tip()

# Serial dilution across A1 to A{info["num_dilutions"]+1}
for i in range({info["num_dilutions"]}):
    source = plate.rows()[0][i]
    dest = plate.rows()[0][i+1]
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, source)
    pipette.dispense({info["volume"]}, dest)
    pipette.mix(3, {info["volume"]}, dest)
    pipette.drop_tip()
"""
    else:
        protocol_body = f"""
# Add diluent to wells (1-channel, individual wells)
for i in range(1, {info["num_dilutions"]+1}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, diluent)
    pipette.dispense({info["volume"]}, plate.wells()[i])
    pipette.drop_tip()

# Add sample to first well
pipette.pick_up_tip()
pipette.aspirate({info["volume"]}, sample)
pipette.dispense({info["volume"]}, plate.wells()[0])
pipette.drop_tip()

# Serial dilution
for i in range({info["num_dilutions"]}):
    source = plate.wells()[i]
    dest = plate.wells()[i+1]
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, source)
    pipette.dispense({info["volume"]}, dest)
    pipette.mix(3, {info["volume"]}, dest)
    pipette.drop_tip()
"""
    
    return header + protocol_body

def generate_pcr_setup_protocol(info: dict) -> str:
    """Generate PCR setup protocol code."""
    
    return f"""# PCR Setup Protocol
# Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "D2")
reagent_plate = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

master_mix = reagent_plate.wells()[0]
primer_mix = reagent_plate.wells()[1]
template = reagent_plate.wells()[2]

# Distribute master mix
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.7}, master_mix)
    pipette.dispense({info["volume"] * 0.7}, pcr_plate.wells()[i])
    pipette.drop_tip()

# Add primer mix
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.2}, primer_mix)
    pipette.dispense({info["volume"] * 0.2}, pcr_plate.wells()[i])
    pipette.drop_tip()

# Add template DNA
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.1}, template)
    pipette.dispense({info["volume"] * 0.1}, pcr_plate.wells()[i])
    pipette.mix(3, {info["volume"] * 0.5}, pcr_plate.wells()[i])
    pipette.drop_tip()
"""

def generate_plate_washing_protocol(info: dict) -> str:
    """Generate plate washing protocol code."""
    
    return f"""# Plate Washing Protocol
# Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
plate = protocol.load_labware("{info["plate_type"]}", "D2")
trough = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

wash_buffer = trough.wells()[0]

# Wash cycle (3 times)
for cycle in range(3):
    # Add wash buffer
    for i in range({info["num_samples"]}):
        pipette.pick_up_tip()
        pipette.aspirate({info["volume"]}, wash_buffer)
        pipette.dispense({info["volume"]}, plate.wells()[i])
        pipette.drop_tip()
    
    # Incubate
    protocol.delay(minutes=2)
    
    # Remove wash buffer
    for i in range({info["num_samples"]}):
        pipette.pick_up_tip()
        pipette.aspirate({info["volume"]}, plate.wells()[i])
        pipette.dispense({info["volume"]}, trash)
        pipette.drop_tip()
"""

def generate_sample_transfer_protocol(info: dict) -> str:
    """Generate sample transfer protocol code."""
    
    return f"""# Sample Transfer Protocol
# Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
source_plate = protocol.load_labware("{info["plate_type"]}", "D2")
dest_plate = protocol.load_labware("{info["plate_type"]}", "D3")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

# Transfer samples from source to destination
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, source_plate.wells()[i])
    pipette.dispense({info["volume"]}, dest_plate.wells()[i])
    pipette.drop_tip()
"""

def generate_cell_culture_protocol(info: dict) -> str:
    """Generate cell culture protocol code."""
    
    return f"""# Cell Culture Protocol
# Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
culture_plate = protocol.load_labware("{info["plate_type"]}", "D2")
trough = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

media = trough.wells()[0]
cells = trough.wells()[1]

# Add media to wells
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.8}, media)
    pipette.dispense({info["volume"] * 0.8}, culture_plate.wells()[i])
    pipette.drop_tip()

# Add cells
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.2}, cells)
    pipette.dispense({info["volume"] * 0.2}, culture_plate.wells()[i])
    pipette.mix(3, {info["volume"] * 0.4}, culture_plate.wells()[i])
    pipette.drop_tip()
"""

def generate_enzyme_assay_protocol(info: dict) -> str:
    """Generate enzyme assay protocol code."""
    
    return f"""# Enzyme Assay Protocol
# Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
assay_plate = protocol.load_labware("{info["plate_type"]}", "D2")
trough = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

substrate = trough.wells()[0]
enzyme = trough.wells()[1]
buffer = trough.wells()[2]

# Add buffer
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.6}, buffer)
    pipette.dispense({info["volume"] * 0.6}, assay_plate.wells()[i])
    pipette.drop_tip()

# Add substrate
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.3}, substrate)
    pipette.dispense({info["volume"] * 0.3}, assay_plate.wells()[i])
    pipette.drop_tip()

# Add enzyme to start reaction
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"] * 0.1}, enzyme)
    pipette.dispense({info["volume"] * 0.1}, assay_plate.wells()[i])
    pipette.mix(2, {info["volume"] * 0.3}, assay_plate.wells()[i])
    pipette.drop_tip()
"""

def generate_generic_protocol(info: dict) -> str:
    """Generate a generic protocol for unrecognized experiment types."""
    
    return f"""# Generic Laboratory Protocol
# Type: {info["type"]}, Samples: {info["num_samples"]}, Volume: {info["volume"]}µL

pipette = protocol.load_instrument("{info["pipette_type"]}", "{info["pipette_mount"]}")
tiprack = protocol.load_labware("{info["tip_type"]}", "A1")
plate = protocol.load_labware("{info["plate_type"]}", "D2")
trough = protocol.load_labware("{info["source_labware"]}", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

reagent = trough.wells()[0]

# Basic liquid handling - distribute reagent to samples
for i in range({info["num_samples"]}):
    pipette.pick_up_tip()
    pipette.aspirate({info["volume"]}, reagent)
    pipette.dispense({info["volume"]}, plate.wells()[i])
    pipette.drop_tip()

protocol.comment("Generic protocol completed. Please review and modify as needed.")
"""

# Protocol Generator Agent
ProtocolGeneratorAgent = Agent(
    name="ProtocolGeneratorAgent",
    instructions=(
        "You generate Python code for Opentrons protocols based on experiment descriptions. "
        "Use the generate_general_protocol tool to create appropriate protocol code. "
        "Support multiple experiment types including serial dilutions, PCR setup, plate washing, "
        "sample transfers, cell culture, and enzyme assays. "
        "Return only the raw Python code that goes inside the run(protocol) function. "
        "Parse the experiment type and parameters from the clean_prompt and generate appropriate code."
    ),
    tools=[generate_general_protocol],
    output_type=str,
    model_settings=ModelSettings(temperature=0.1),
    tool_use_behavior="stop_on_first_tool"
)