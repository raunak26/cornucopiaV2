from agents import Agent, function_tool, ModelSettings
import json
@function_tool
def clarify_request(raw: str) -> str:
    """
    Enhances a user's serial dilution request by filling in missing details,
    but preserves any specific information the user provides.
    Returns a JSON string with keys: confirmation, clean_prompt.
    """
    import re
    prompt = raw.strip()
    lower_prompt = prompt.lower()

    # Only trigger if the user mentions serial dilution
    if "serial dilution" in lower_prompt:
        # Defaults
        defaults = {
            "num_dilutions": 5,
            "dilution_factor": 2,
            "starting_volume_ul": 100,
            "plate_type": "nest_96_wellplate_200ul_flat"
        }

        # Heuristics to check for user-supplied details
        has_plate = any(word in lower_prompt for word in ["plate", "wellplate", "96", "384"])
        has_volume = any(unit in lower_prompt for unit in ["ul", "µl", "ml"])
        has_dilution = bool(re.search(r"1:\d+", lower_prompt) or "dilution factor" in lower_prompt)
        has_location = any(loc in lower_prompt for loc in ["column", "row", "well", "trough", "leftmost", "rightmost", "first", "last"])

        # Build enhancements
        enhancements = []
        if not has_dilution:
            enhancements.append(f"dilution factor 1:{defaults['dilution_factor']}")
        if not has_volume:
            enhancements.append(f"starting volume {defaults['starting_volume_ul']}µL")
        if not has_plate:
            enhancements.append(f"using a {defaults['plate_type']}")
        if not has_location:
            enhancements.append("starting at the first well")

        # If the prompt is extremely vague, use defaults
        if prompt.lower().strip() in ["do a serial dilution", "serial dilution"]:
            clean_prompt = (
                f"Perform a {defaults['num_dilutions']}-step 1:{defaults['dilution_factor']} serial dilution "
                f"starting at {defaults['starting_volume_ul']}µL in a {defaults['plate_type']}."
            )
            confirmation = (
                f"You want a {defaults['num_dilutions']}-step 1:{defaults['dilution_factor']} serial dilution "
                f"starting at {defaults['starting_volume_ul']}µL in a 96-well plate?"
            )
        else:
            # Otherwise, preserve the user's prompt and append missing info
            if enhancements:
                clean_prompt = prompt.rstrip(".") + " (" + "; ".join(enhancements) + ")."
            else:
                clean_prompt = prompt if prompt.endswith(".") else prompt + "."
            confirmation = f"Just to confirm: {clean_prompt}"

        return json.dumps({
            "confirmation": confirmation,
            "clean_prompt": clean_prompt
        })

    # Default fallback if input is vague or not about serial dilution
    return json.dumps({
        "confirmation": "Hi! I can help you generate a lab protocol. What would you like to do (e.g., 'run a serial dilution')?",
        "clean_prompt": ""
    })

PromptCreatorAgent = Agent(
    name="PromptCreatorAgent",
    instructions="""
You take a user's vague lab request like 'do a serial dilution' and produce JSON via the clarify_request tool.
Return only a JSON string with keys 'confirmation' and 'clean_prompt'. No explanations.
""".strip(),
    tools=[clarify_request],
    output_type=str,
    model_settings=ModelSettings(temperature=0.0),
    tool_use_behavior="stop_on_first_tool"
)

