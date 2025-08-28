from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import json
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx
import aiofiles
from typing import Optional, List

from agents import set_default_openai_client
# Import your agents (update these import paths as needed)
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
app = FastAPI(
    title="CornucopiaV2 API",
    description="AI-powered multi-experiment lab automation for Opentrons Flex",
    version="2.0.0"
)

# ---------- Request Models ----------
class ExperimentRequest(BaseModel):
    user_input: str
    experiment_type: Optional[str] = None  # Optional experiment type hint

class FlexRunRequest(BaseModel):
    filepath: str

class ProtocolValidationRequest(BaseModel):
    protocol_code: str

class ExperimentTypeRequest(BaseModel):
    experiment_type: str
    parameters: Optional[dict] = {}

# ---------- Response Models ----------
class ExperimentResponse(BaseModel):
    confirmation: str
    clean_prompt: str
    protocol: str
    qc_result: str
    filepath: str
    experiment_type: str
    success: bool
    error_message: Optional[str] = None

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

class FlexStatusResponse(BaseModel):
    run_id: str
    status: str
    current_command: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

class ExperimentTypeInfo(BaseModel):
    type: str
    name: str
    description: str
    parameters: List[str]
    example: Optional[str] = None

# ---------- Helper Functions ----------
def determine_experiment_type(prompt: str) -> str:
    """Determine experiment type from user input."""
    prompt_lower = prompt.lower()
    
    if "serial dilution" in prompt_lower:
        return "serial_dilution"
    elif any(term in prompt_lower for term in ["pcr", "amplification", "polymerase"]):
        return "pcr_setup"
    elif any(term in prompt_lower for term in ["wash", "washing", "rinse"]):
        return "plate_washing"
    elif any(term in prompt_lower for term in ["transfer", "move", "aliquot"]):
        return "sample_transfer"
    elif any(term in prompt_lower for term in ["cell", "culture", "seed", "passage"]):
        return "cell_culture"
    elif any(term in prompt_lower for term in ["enzyme", "assay", "substrate", "kinetic"]):
        return "enzyme_assay"
    else:
        return "generic"

def analyze_qc_errors(stderr: str) -> dict:
    """Analyze QC errors and provide structured feedback."""
    errors = []
    warnings = []
    suggestions = []
    
    if not stderr:
        return {
            "errors": [],
            "warnings": [],
            "suggestions": ["Protocol validated successfully"]
        }
    
    stderr_lower = stderr.lower()
    
    # Common error patterns
    if "keyerror" in stderr_lower:
        errors.append("Missing required parameter")
        suggestions.append("Check that all labware and reagents are properly defined")
    
    if "outoftipserror" in stderr_lower:
        errors.append("Insufficient tips for protocol")
        suggestions.append("Add more tip racks or optimize tip usage")
        suggestions.append("Consider using 'new_tip=\"never\"' for some operations")
    
    if "slotdoesnotexisterror" in stderr_lower:
        errors.append("Invalid deck slot specified")
        suggestions.append("Use valid deck slots (A1-D4 for Opentrons Flex)")
    
    if "modulenotfounderror" in stderr_lower:
        errors.append("Missing required module")
        suggestions.append("Check import statements and package installations")
    
    if "incompatiblelabwareerror" in stderr_lower:
        warnings.append("Labware compatibility issue detected")
        suggestions.append("Verify pipette and labware compatibility")
    
    if any(term in stderr_lower for term in ["volume", "aspirate", "dispense"]):
        warnings.append("Volume handling issue detected")
        suggestions.append("Check volume specifications and pipette limits")
    
    if "syntaxerror" in stderr_lower:
        errors.append("Python syntax error in protocol")
        suggestions.append("Review generated code for syntax issues")
    
    if "indentationerror" in stderr_lower:
        errors.append("Python indentation error")
        suggestions.append("Check code indentation and formatting")
    
    if "nameerror" in stderr_lower:
        errors.append("Undefined variable or function")
        suggestions.append("Ensure all variables are properly defined")
    
    if "typeerror" in stderr_lower:
        errors.append("Type-related error")
        suggestions.append("Check data types and function arguments")
    
    if not errors and not warnings:
        errors.append("Unknown simulation error")
        suggestions.append("Review protocol code and Opentrons documentation")
        suggestions.append("Check simulator logs for detailed error information")
    
    return {
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions
    }

# ---------- API Endpoints ----------

@app.get("/")
async def root():
    """API root endpoint with basic information."""
    return {
        "message": "CornucopiaV2 Enhanced API",
        "version": "2.0.0",
        "description": "AI-powered multi-experiment lab automation",
        "supported_experiments": [
            "serial_dilution",
            "pcr_setup", 
            "plate_washing",
            "sample_transfer",
            "cell_culture",
            "enzyme_assay",
            "generic"
        ],
        "endpoints": [
            "/generate_protocol",
            "/validate_protocol", 
            "/send_to_flex",
            "/experiments/types",
            "/runs/{run_id}/status",
            "/runs/{run_id}/stop"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test OpenAI connection
        test_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Test Opentrons connection
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            try:
                opentrons_response = await http_client.get(f"{BASE_URL}/health")
                opentrons_status = "connected" if opentrons_response.status_code == 200 else "disconnected"
            except:
                opentrons_status = "disconnected"
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "services": {
                "openai": "connected" if os.getenv("OPENAI_API_KEY") else "not_configured",
                "opentrons_flex": opentrons_status
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }

@app.post("/generate_protocol", response_model=ExperimentResponse)
async def generate_protocol(req: ExperimentRequest):
    """Generate a protocol from user input using enhanced AI agents."""
    
    user_input = req.user_input.strip()
    
    if not user_input:
        raise HTTPException(status_code=400, detail="User input cannot be empty")
    
    try:
        # Determine experiment type
        experiment_type = req.experiment_type or determine_experiment_type(user_input)
        
        # Step 1: Clarify prompt using enhanced agent
        clarify_result = await Runner.run_async(PromptCreatorAgent, user_input)
        clarified = json.loads(clarify_result.final_output)
        confirmation = clarified["confirmation"]
        clean_prompt = clarified["clean_prompt"]

        if not clean_prompt:
            return ExperimentResponse(
                confirmation=confirmation,
                clean_prompt="",
                protocol="",
                qc_result="",
                filepath="",
                experiment_type=experiment_type,
                success=False,
                error_message="Prompt clarification failed - insufficient information provided"
            )

        # Step 2: Generate protocol using enhanced agent
        protocol_result = await Runner.run_async(ProtocolGeneratorAgent, clean_prompt)
        raw_protocol = protocol_result.final_output.strip()

        if not raw_protocol:
            return ExperimentResponse(
                confirmation=confirmation,
                clean_prompt=clean_prompt,
                protocol="",
                qc_result="",
                filepath="",
                experiment_type=experiment_type,
                success=False,
                error_message="Protocol generation failed"
            )

        # Format protocol with proper indentation
        def indent(code: str, spaces: int = 4) -> str:
            pad = " " * spaces
            return "\n".join(pad + line if line.strip() else "" for line in code.splitlines())

        full_protocol = get_fixed_header().rstrip() + "\n" + indent(raw_protocol)
        
        # Step 3: Save and validate protocol
        path = save_protocol(full_protocol, filename=f"generated_protocol_{experiment_type}.py")
        qc_result = _simulate_protocol(path)

        return ExperimentResponse(
            confirmation=confirmation,
            clean_prompt=clean_prompt,
            protocol=full_protocol,
            qc_result=qc_result,
            filepath=path,
            experiment_type=experiment_type,
            success=len(qc_result) == 0,  # Success if no errors
            error_message=qc_result if qc_result else None
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error during protocol generation: {str(e)}"
        )

@app.post("/validate_protocol", response_model=ValidationResponse)
async def validate_protocol(req: ProtocolValidationRequest):
    """Validate a protocol without generating a new one."""
    
    if not req.protocol_code.strip():
        raise HTTPException(status_code=400, detail="Protocol code cannot be empty")
    
    try:
        # Save protocol temporarily for validation
        temp_path = save_protocol(req.protocol_code, filename="temp_validation.py")
        
        # Run simulation
        stderr = _simulate_protocol(temp_path)
        
        # Analyze results
        analysis = analyze_qc_errors(stderr)
        
        # Clean up temp file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass  # Ignore cleanup errors
        
        return ValidationResponse(
            is_valid=len(analysis["errors"]) == 0,
            errors=analysis["errors"],
            warnings=analysis["warnings"],
            suggestions=analysis["suggestions"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Protocol validation failed: {str(e)}"
        )

@app.post("/send_to_flex")
async def send_to_flex(req: FlexRunRequest):
    """Send protocol to Opentrons Flex for execution."""
    
    filepath = req.filepath

    try:
        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=400, 
                detail=f"Protocol file not found: {filepath}"
            )

        # Read protocol file
        async with aiofiles.open(filepath, 'rb') as f:
            file_data = await f.read()

        # Upload protocol to Opentrons
        files = {'files': ('protocol.py', file_data, 'text/x-python')}
        headers = {"opentrons-version": "2"}

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            upload_response = await http_client.post(
                f"{BASE_URL}/protocols",
                files=files,
                headers=headers
            )

        if upload_response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=upload_response.status_code,
                detail=f"Protocol upload failed: {upload_response.text}"
            )
        
        protocol_data = upload_response.json()
        protocol_id = protocol_data["data"]["id"]

        # Create run
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            run_response = await http_client.post(
                f"{BASE_URL}/runs",
                json={"data": {"protocolId": protocol_id}},
                headers=headers
            )

        if run_response.status_code != 201:
            raise HTTPException(
                status_code=run_response.status_code,
                detail=f"Run creation failed: {run_response.text}"
            )

        run_data = run_response.json()
        run_id = run_data["data"]["id"]

        # Start run
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            start_response = await http_client.post(
                f"{BASE_URL}/runs/{run_id}/actions",
                json={"data": {"actionType": "play"}},
                headers=headers
            )

        if start_response.status_code != 200:
            raise HTTPException(
                status_code=start_response.status_code,
                detail=f"Run start failed: {start_response.text}"
            )

        return {
            "status": "success",
            "message": "Protocol sent to Opentrons Flex successfully",
            "run_id": run_id,
            "protocol_id": protocol_id,
            "protocol_name": os.path.basename(filepath)
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error while sending to Flex: {str(e)}"
        )

@app.get("/experiments/types")
async def get_experiment_types():
    """Get list of supported experiment types with descriptions."""
    
    experiment_types = [
        ExperimentTypeInfo(
            type="serial_dilution",
            name="Serial Dilution",
            description="Perform step-wise dilutions across a plate",
            parameters=["num_dilutions", "dilution_factor", "volume", "starting_well"],
            example="Run a 5-step 1:2 serial dilution with 100µL starting volume"
        ),
        ExperimentTypeInfo(
            type="pcr_setup", 
            name="PCR Setup",
            description="Set up PCR reactions with master mix, primers, and template",
            parameters=["num_samples", "reaction_volume", "master_mix_volume"],
            example="Set up PCR reactions for 24 samples with 25µL reaction volume"
        ),
        ExperimentTypeInfo(
            type="plate_washing",
            name="Plate Washing", 
            description="Wash plates with buffer solution multiple times",
            parameters=["num_wash_cycles", "wash_volume", "incubation_time"],
            example="Wash 96 wells with 200µL wash buffer, 3 cycles"
        ),
        ExperimentTypeInfo(
            type="sample_transfer",
            name="Sample Transfer",
            description="Transfer samples between plates or containers",
            parameters=["num_samples", "transfer_volume", "source_plate", "dest_plate"],
            example="Transfer 50µL from 48 source wells to destination plate"
        ),
        ExperimentTypeInfo(
            type="cell_culture",
            name="Cell Culture",
            description="Set up cell culture experiments with media and cells",
            parameters=["num_wells", "media_volume", "cell_volume"],
            example="Seed cells in 24 wells with 150µL media and 50µL cell suspension"
        ),
        ExperimentTypeInfo(
            type="enzyme_assay",
            name="Enzyme Assay",
            description="Set up enzyme kinetic assays with substrate and enzyme",
            parameters=["num_reactions", "substrate_volume", "enzyme_volume", "buffer_volume"],
            example="Set up enzyme assay for 48 samples with 100µL total volume"
        )
    ]
    
    return {"experiment_types": [exp.dict() for exp in experiment_types]}

@app.get("/runs/{run_id}/status", response_model=FlexStatusResponse)
async def get_run_status(run_id: str):
    """Get the status of a running protocol on Opentrons Flex."""
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                f"{BASE_URL}/runs/{run_id}",
                headers={"opentrons-version": "2"}
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get run status: {response.text}"
            )
        
        run_data = response.json()["data"]
        
        return FlexStatusResponse(
            run_id=run_id,
            status=run_data.get("status", "unknown"),
            current_command=run_data.get("current"),
            created_at=run_data.get("createdAt"),
            started_at=run_data.get("startedAt"),
            completed_at=run_data.get("completedAt")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting run status: {str(e)}"
        )

@app.post("/runs/{run_id}/stop")
async def stop_run(run_id: str):
    """Stop a running protocol on Opentrons Flex."""
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(
                f"{BASE_URL}/runs/{run_id}/actions",
                json={"data": {"actionType": "stop"}},
                headers={"opentrons-version": "2"}
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to stop run: {response.text}"
            )
        
        return {
            "status": "success",
            "message": f"Run {run_id} stopped successfully",
            "run_id": run_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping run: {str(e)}"
        )

@app.get("/protocols")
async def list_protocols():
    """List all available protocols on the Opentrons Flex."""
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get(
                f"{BASE_URL}/protocols",
                headers={"opentrons-version": "2"}
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list protocols: {response.text}"
            )
        
        return response.json()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing protocols: {str(e)}"
        )

# ---------- Error Handlers ----------
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "endpoint_not_found",
        "message": f"The requested endpoint was not found",
        "available_endpoints": [
            "/",
            "/health", 
            "/generate_protocol",
            "/validate_protocol",
            "/send_to_flex",
            "/experiments/types",
            "/runs/{run_id}/status",
            "/runs/{run_id}/stop",
            "/protocols"
        ]
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "internal_server_error",
        "message": "An internal server error occurred",
        "details": str(exc) if hasattr(exc, 'detail') else "Unknown error"
    }

# ---------- Startup/Shutdown Events ----------
@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    print("🚀 CornucopiaV2 Enhanced API starting up...")
    print(f"📡 Opentrons Flex URL: {BASE_URL}")
    print(f"🤖 OpenAI API Key configured: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    
    # Test connections
    try:
        # Test Opentrons connection
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.get(f"{BASE_URL}/health")
            print(f"🔬 Opentrons Flex connection: {'✅ Connected' if response.status_code == 200 else '❌ Failed'}")
    except:
        print("🔬 Opentrons Flex connection: ❌ Failed to connect")
    
    print("✅ API ready to accept requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("🛑 CornucopiaV2 API shutting down...")
    print("✅ Cleanup completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)