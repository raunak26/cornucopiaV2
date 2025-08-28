from agents import Agent, function_tool, ModelSettings
import json
import re

@function_tool
def clarify_experiment_request(raw: str) -> str:
    """
    Enhances any lab experiment request by filling in missing details,
    but preserves any specific information the user provides.
    Returns a JSON string with keys: confirmation, clean_prompt.
    """
    
    prompt = raw.strip()
    lower_prompt = prompt.lower()
    
    # Determine experiment type and set appropriate defaults
    experiment_type = determine_experiment_type(lower_prompt)
    defaults = get_experiment_defaults(experiment_type)
    
    # Extract user-specified parameters
    user_params = extract_user_parameters(prompt)
    
    # Merge user parameters with defaults
    final_params = {**defaults, **user_params}
    
    # Generate confirmation and clean prompt based on experiment type
    if experiment_type == "serial_dilution":
        return handle_serial_dilution(prompt, lower_prompt, final_params)
    elif experiment_type == "pcr_setup":
        return handle_pcr_setup(prompt, lower_prompt, final_params)
    elif experiment_type == "plate_washing":
        return handle_plate_washing(prompt, lower_prompt, final_params)
    elif experiment_type == "sample_transfer":
        return handle_sample_transfer(prompt, lower_prompt, final_params)
    elif experiment_type == "cell_culture":
        return handle_cell_culture(prompt, lower_prompt, final_params)
    elif experiment_type == "enzyme_assay":
        return handle_enzyme_assay(prompt, lower_prompt, final_params)
    else:
        return handle_generic_experiment(prompt, lower_prompt, final_params)

def determine_experiment_type(prompt_lower: str) -> str:
    """Determine the type of experiment based on keywords in the prompt."""
    
    if "serial dilution" in prompt_lower:
        return "serial_dilution"
    elif any(term in prompt_lower for term in ["pcr", "amplification", "reaction mix", "polymerase"]):
        return "pcr_setup"
    elif any(term in prompt_lower for term in ["wash", "washing", "rinse", "clean"]):
        return "plate_washing"
    elif any(term in prompt_lower for term in ["transfer", "move", "aliquot", "pipette"]):
        return "sample_transfer"
    elif any(term in prompt_lower for term in ["cell", "culture", "media", "passage", "seed"]):
        return "cell_culture"
    elif any(term in prompt_lower for term in ["enzyme", "assay", "substrate", "kinetic", "activity"]):
        return "enzyme_assay"
    else:
        return "generic"

def get_experiment_defaults(experiment_type: str) -> dict:
    """Get default parameters for each experiment type."""
    
    defaults_map = {
        "serial_dilution": {
            "num_dilutions": 5,
            "dilution_factor": 2,
            "starting_volume_ul": 100,
            "plate_type": "nest_96_wellplate_200ul_flat",
            "num_samples": 8
        },
        "pcr_setup": {
            "num_samples": 24,
            "reaction_volume_ul": 25,
            "plate_type": "nest_96_wellplate_100ul_pcr_full_skirt",
            "master_mix_volume": 17.5,
            "primer_volume": 5,
            "template_volume": 2.5
        },
        "plate_washing": {
            "num_samples": 96,
            "wash_volume_ul": 200,
            "num_wash_cycles": 3,
            "incubation_time_min": 2,
            "plate_type": "nest_96_wellplate_200ul_flat"
        },
        "sample_transfer": {
            "num_samples": 24,
            "transfer_volume_ul": 100,
            "plate_type": "nest_96_wellplate_200ul_flat"
        },
        "cell_culture": {
            "num_samples": 24,
            "media_volume_ul": 150,
            "cell_volume_ul": 50,
            "plate_type": "nest_96_wellplate_200ul_flat"
        },
        "enzyme_assay": {
            "num_samples": 48,
            "total_volume_ul": 100,
            "substrate_volume": 30,
            "enzyme_volume": 10,
            "buffer_volume": 60,
            "plate_type": "nest_96_wellplate_200ul_flat"
        },
        "generic": {
            "num_samples": 24,
            "volume_ul": 100,
            "plate_type": "nest_96_wellplate_200ul_flat"
        }
    }
    
    return defaults_map.get(experiment_type, defaults_map["generic"])

def extract_user_parameters(prompt: str) -> dict:
    """Extract user-specified parameters from the prompt."""
    
    params = {}
    prompt_lower = prompt.lower()
    
    # Extract volumes
    volume_match = re.search(r'(\d+)\s*(?:ul|µl|microliter|microlitre)', prompt_lower)
    if volume_match:
        params["volume_ul"] = int(volume_match.group(1))
        params["starting_volume_ul"] = int(volume_match.group(1))
        params["reaction_volume_ul"] = int(volume_match.group(1))
        params["transfer_volume_ul"] = int(volume_match.group(1))
        params["wash_volume_ul"] = int(volume_match.group(1))
        params["total_volume_ul"] = int(volume_match.group(1))
        params["media_volume_ul"] = int(volume_match.group(1))
    
    # Extract sample numbers
    samples_match = re.search(r'(\d+)\s*(?:samples?|wells?)', prompt_lower)
    if samples_match:
        params["num_samples"] = int(samples_match.group(1))
    
    # Extract dilution parameters
    dilution_match = re.search(r'1:(\d+)|(\d+)x?\s*dilution', prompt_lower)
    if dilution_match:
        params["dilution_factor"] = int(dilution_match.group(1) or dilution_match.group(2))
    
    steps_match = re.search(r'(\d+)\s*(?:steps?|dilutions?)', prompt_lower)
    if steps_match:
        params["num_dilutions"] = int(steps_match.group(1))
    
    # Extract time parameters
    time_match = re.search(r'(\d+)\s*(?:min|minutes?)', prompt_lower)
    if time_match:
        params["incubation_time_min"] = int(time_match.group(1))
    
    # Extract wash cycles
    wash_match = re.search(r'(\d+)\s*(?:wash|washes?|cycles?)', prompt_lower)
    if wash_match:
        params["num_wash_cycles"] = int(wash_match.group(1))
    
    # Extract plate type preferences
    if "pcr" in prompt_lower:
        params["plate_type"] = "nest_96_wellplate_100ul_pcr_full_skirt"
    elif "384" in prompt_lower:
        params["plate_type"] = "corning_384_wellplate_112ul_flat"
    
    return params

def handle_serial_dilution(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle serial dilution experiment clarification."""
    
    # Check what user specified vs what we're assuming
    enhancements = []
    
    if not re.search(r"1:\d+", prompt) and not re.search(r"\d+x?\s*dilution", prompt):
        enhancements.append(f"dilution factor 1:{params['dilution_factor']}")
    
    if not re.search(r"\d+\s*(?:ul|µl)", prompt):
        enhancements.append(f"starting volume {params['starting_volume_ul']}µL")
    
    if not re.search(r"\d+\s*(?:steps?|dilutions?)", prompt):
        enhancements.append(f"{params['num_dilutions']} dilution steps")
    
    if not re.search(r"plate|wellplate", prompt):
        enhancements.append(f"using a 96-well plate")
    
    # Generate clean prompt
    if prompt.lower().strip() in ["do a serial dilution", "serial dilution", "run serial dilution"]:
        clean_prompt = (
            f"Perform a {params['num_dilutions']}-step 1:{params['dilution_factor']} serial dilution "
            f"starting with {params['starting_volume_ul']}µL in a 96-well plate."
        )
    else:
        if enhancements:
            clean_prompt = prompt.rstrip(".") + " (" + "; ".join(enhancements) + ")."
        else:
            clean_prompt = prompt if prompt.endswith(".") else prompt + "."
    
    confirmation = f"I'll set up a serial dilution with {params['num_dilutions']} steps at 1:{params['dilution_factor']} dilution factor using {params['starting_volume_ul']}µL per well. Is this correct?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_pcr_setup(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle PCR setup experiment clarification."""
    
    clean_prompt = f"Set up PCR reactions for {params['num_samples']} samples with {params['reaction_volume_ul']}µL total reaction volume using PCR plates."
    confirmation = f"I'll prepare {params['num_samples']} PCR reactions with {params['reaction_volume_ul']}µL each. Master mix: {params['master_mix_volume']}µL, primers: {params['primer_volume']}µL, template: {params['template_volume']}µL per reaction. Correct?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_plate_washing(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle plate washing experiment clarification."""
    
    clean_prompt = f"Wash {params['num_samples']} wells with {params['wash_volume_ul']}µL wash buffer, {params['num_wash_cycles']} cycles, {params['incubation_time_min']} minutes incubation per cycle."
    confirmation = f"I'll wash {params['num_samples']} wells using {params['wash_volume_ul']}µL per wash, repeating {params['num_wash_cycles']} times with {params['incubation_time_min']} minute incubations. Sound good?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_sample_transfer(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle sample transfer experiment clarification."""
    
    clean_prompt = f"Transfer {params['transfer_volume_ul']}µL from {params['num_samples']} source wells to destination wells."
    confirmation = f"I'll transfer {params['transfer_volume_ul']}µL from {params['num_samples']} source wells to corresponding destination wells. Is this what you need?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_cell_culture(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle cell culture experiment clarification."""
    
    clean_prompt = f"Set up cell culture for {params['num_samples']} wells with {params['media_volume_ul']}µL media and {params['cell_volume_ul']}µL cell suspension per well."
    confirmation = f"I'll prepare {params['num_samples']} cell culture wells with {params['media_volume_ul']}µL media and {params['cell_volume_ul']}µL cells each. Does this match your protocol?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_enzyme_assay(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle enzyme assay experiment clarification."""
    
    clean_prompt = f"Set up enzyme assay for {params['num_samples']} reactions with {params['total_volume_ul']}µL total volume: {params['buffer_volume']}µL buffer, {params['substrate_volume']}µL substrate, {params['enzyme_volume']}µL enzyme."
    confirmation = f"I'll prepare {params['num_samples']} enzyme assay reactions ({params['total_volume_ul']}µL each) with buffer, substrate, and enzyme. Ready to proceed?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

def handle_generic_experiment(prompt: str, lower_prompt: str, params: dict) -> str:
    """Handle generic/unrecognized experiment clarification."""
    
    if not prompt or len(prompt.strip()) < 5:
        return json.dumps({
            "confirmation": "Hi! I can help you generate lab protocols. What experiment would you like to run? (e.g., 'serial dilution', 'PCR setup', 'plate washing', 'sample transfer')",
            "clean_prompt": ""
        })
    
    clean_prompt = f"Perform laboratory procedure: {prompt} for {params['num_samples']} samples using {params['volume_ul']}µL per sample."
    confirmation = f"I'll help you set up: {prompt}. I'll assume {params['num_samples']} samples with {params['volume_ul']}µL per sample unless you specify otherwise. Is this correct?"
    
    return json.dumps({
        "confirmation": confirmation,
        "clean_prompt": clean_prompt
    })

# Prompt Creator Agent
PromptCreatorAgent = Agent(
    name="PromptCreatorAgent",
    instructions="""
You take a user's lab experiment request and enhance it with appropriate details.
You support multiple experiment types:
- Serial dilutions
- PCR setup
- Plate washing
- Sample transfers  
- Cell culture
- Enzyme assays
- Generic lab procedures

Use the clarify_experiment_request tool to process the user's input.
Return only a JSON string with keys 'confirmation' and 'clean_prompt'. No explanations.
The confirmation should be conversational and ask for user validation.
The clean_prompt should be detailed and complete for protocol generation.
""".strip(),
    tools=[clarify_experiment_request],
    output_type=str,
    model_settings=ModelSettings(temperature=0.0),
    tool_use_behavior="stop_on_first_tool"
)