from agents import Agent, function_tool, ModelSettings
import subprocess

# ✅ Raw callable version for direct use in main.py
def _simulate_protocol(path: str) -> str:
    try:
        proc = subprocess.run(
            ["opentrons_simulate", path],
            capture_output=True, text=True, check=True
        )
        return ""  # no error
    except subprocess.CalledProcessError as e:
        return e.stderr

def _extract_missing(stderr: str) -> str:
    if "KeyError" in stderr:
        return "missing dictionary key"
    # Add more heuristics if needed
    return "unknown error"

# ✅ FunctionTool wrappers for agent use
@function_tool
def simulate_protocol_tool(path: str) -> str:
    return _simulate_protocol(path)

@function_tool
def extract_missing_tool(stderr: str) -> str:
    return _extract_missing(stderr)

# ✅ Agent using tools
QCAgent = Agent(
    name="QCAgent",
    instructions="You simulate a .py and return errors. Use simulate_protocol_tool then extract_missing_tool.",
    tools=[simulate_protocol_tool, extract_missing_tool],
    model_settings=ModelSettings(temperature=0.0),
    tool_use_behavior="run_llm_again"
)
