

from agents import Runner
from cornucopia_agents.prompt_creator import PromptCreatorAgent
from cornucopia_agents.protocol_generator import ProtocolGeneratorAgent
from cornucopia_agents.qc_agent import QCAgent
from utils.fixed_header import get_fixed_header
from utils.io_helpers import save_protocol
import json

def run_protocol_pipeline(user_prompt: str):
    """
    Run the full Cornucopia agent pipeline:
    1. Clarify prompt
    2. Generate protocol
    3. Save .py
    4. Simulate & QC
    Returns:
        dict with keys:
            confirmation (str)
            clean_prompt (str)
            protocol_code (str)
            path (str)
            qc_error (str or None)
    """
    results = {}

    # Step 1: Clarify prompt
    clarify_result = Runner.run_sync(PromptCreatorAgent, user_prompt)
    clarified = json.loads(clarify_result.final_output)
    results["confirmation"] = clarified["confirmation"]
    clean_prompt = clarified["clean_prompt"]
    results["clean_prompt"] = clean_prompt

    # Step 2: Generate protocol code
    protocol_result = Runner.run_sync(ProtocolGeneratorAgent, clean_prompt)
    run_block = protocol_result.final_output.strip()
    full_code = get_fixed_header().rstrip() + "\n" + run_block
    results["protocol_code"] = full_code

    # Step 3: Save to file
    path = save_protocol(full_code)
    results["path"] = path

    # Step 4: Simulate & QC
    qc_result = Runner.run_sync(QCAgent, path)
    results["qc_error"] = qc_result.final_output.strip() or None

    return results
