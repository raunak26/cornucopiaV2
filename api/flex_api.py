from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx
import aiofiles

from agents import set_default_openai_client
from cornucopia_agents.prompt_creator import PromptCreatorAgent
from cornucopia_agents.protocol_generator import ProtocolGeneratorAgent
from cornucopia_agents.qc_agent import _simulate_protocol
from utils.io_helpers import save_protocol
from utils.fixed_header import get_fixed_header
from agents import Runner

# Load environment variables
load_dotenv()
BASE_URL = os.getenv("OPENTRONS_FLEX_URL", "http://localhost:31950")

# OpenAI client
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=httpx.AsyncClient()
)
set_default_openai_client(client)

# FastAPI app
app = FastAPI()


# ---------- Request Models ----------
class ExperimentRequest(BaseModel):
    user_input: str

class FlexRunRequest(BaseModel):
    filepath: str


# ---------- Generate Protocol ----------
@app.post("/generate_protocol")
async def generate_protocol(req: ExperimentRequest):
    user_input = req.user_input.strip()

    clarify_result = await Runner.run_async(PromptCreatorAgent, user_input)
    clarified = json.loads(clarify_result.final_output)
    confirmation = clarified["confirmation"]
    clean_prompt = clarified["clean_prompt"]

    if not clean_prompt:
        return {"error": "Prompt clarification failed", "confirmation": confirmation}

    protocol_result = await Runner.run_async(ProtocolGeneratorAgent, clean_prompt)
    raw_protocol = protocol_result.final_output.strip()

    def indent(code: str, spaces: int = 4) -> str:
        pad = " " * spaces
        return "\n".join(pad + line if line.strip() else "" for line in code.splitlines())

    full_protocol = get_fixed_header().rstrip() + "\n" + indent(raw_protocol)
    path = save_protocol(full_protocol, filename="generated_protocol.py")
    qc_result = _simulate_protocol(path)

    return {
        "confirmation": confirmation,
        "clean_prompt": clean_prompt,
        "protocol": full_protocol,
        "qc_result": qc_result,
        "filepath": path
    }


# ---------- Send Protocol to Opentrons Flex ----------
@app.post("/send_to_flex")
async def send_to_flex(req: FlexRunRequest):
    filepath = req.filepath

    try:
        if not os.path.exists(filepath):
            raise HTTPException(status_code=400, detail=f"Protocol file not found: {filepath}")

        # Upload protocol
        async with aiofiles.open(filepath, 'rb') as f:
            file_data = await f.read()

        files = {'files': ('protocol.py', file_data, 'text/x-python')}
        headers = {"opentrons-version": "2"}

        async with httpx.AsyncClient() as client:
            upload = await client.post(
                f"{BASE_URL}/protocols",
                files=files,
                headers=headers
            )

        if upload.status_code not in [200, 201]:
            raise HTTPException(
                status_code=upload.status_code,
                detail=f"Upload failed: {upload.text}"
            )
        
        protocol_id = upload.json()["data"]["id"]

        # Create run
        async with httpx.AsyncClient() as client:
            run = await client.post(
                f"{BASE_URL}/runs",
                json={"data": {"protocolId": protocol_id}},
                headers=headers
            )


        if run.status_code != 201:
            raise HTTPException(
                status_code=run.status_code,
                detail=f"Run creation failed: {run.text}"
            )

        run_id = run.json()["data"]["id"]

        # Start run
        async with httpx.AsyncClient() as client:
            start = await client.post(
                f"{BASE_URL}/runs/{run_id}/actions",
                json={"data": {"actionType": "play"}},
                headers=headers
            )

        if start.status_code != 200:
            raise HTTPException(
                status_code=start.status_code,
                detail=f"Run start failed: {start.text}"
            )

        return {"status": "Run started", "run_id": run_id}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
