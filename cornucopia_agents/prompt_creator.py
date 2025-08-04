from agents import Agent, function_tool, ModelSettings
import json

@function_tool
def clarify_request(raw: str) -> str:
    if "serial dilution" in raw.lower():
        details = {
            "num_dilutions": 5,
            "dilution_factor": 2,
            "starting_volume_ul": 100,
            "plate_type": "nest_96_wellplate_200ul_flat"
        }
        cleanup = {
            "confirmation": f"You want a {details['num_dilutions']}-step 1:{details['dilution_factor']} serial dilution starting at {details['starting_volume_ul']}µL in a 96-well plate?",
            "clean_prompt": f"Perform a 1:{details['dilution_factor']} serial dilution using {details['num_dilutions']} wells starting at {details['starting_volume_ul']}µL in a {details['plate_type']}."
        }
        return json.dumps(cleanup)
    # Default fallback if input is vague
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
