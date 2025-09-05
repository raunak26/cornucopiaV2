import streamlit as st
import httpx
from openai import AsyncOpenAI
from agents import set_default_openai_client
from cornucopia_agents.prompt_creator import PromptCreatorAgent
from cornucopia_agents.protocol_generator import ProtocolGeneratorAgent
from cornucopia_agents.qc_agent import QCAgent, _simulate_protocol, _extract_missing
from cornucopia_agents.runner import Runner
from utils.io_helpers import save_protocol
from utils.fixed_header import get_fixed_header

import json
from openai import OpenAI
import os
from agents import set_default_openai_client
from dotenv import load_dotenv
import asyncio

def ensure_event_loop():
    try:
        asyncio.get_event_loop()
    except RuntimeError as e:
        if "no current event loop" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=httpx.AsyncClient()
)
set_default_openai_client(client)

ensure_event_loop()

# --- UI Helper Functions ---
def render_chat(role, message):
    avatar = "🧑" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message)

def render_clarification(confirmation, experiment_type=None):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("**🤖 Clarification:**")
        
        # Show experiment type badge if detected
        if experiment_type:
            experiment_colors = {
                "serial_dilution": "🧬",
                "pcr_setup": "🔬", 
                "plate_washing": "🧽",
                "sample_transfer": "💧",
                "cell_culture": "🦠",
                "enzyme_assay": "⚗️",
                "generic": "🔧"
            }
            icon = experiment_colors.get(experiment_type, "🔧")
            st.markdown(f"{icon} **Detected:** {experiment_type.replace('_', ' ').title()}")
        
        st.info(confirmation)

def render_protocol(code, sent_state, experiment_type=None):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("**🧬 Generated Protocol:**")
        
        # Show protocol summary
        if experiment_type:
            st.markdown(f"*Protocol Type: {experiment_type.replace('_', ' ').title()}*")
        
        st.code(code, language="python")
        
        # --- Send to Opentrons Button & State ---
        sent_key = sent_state['sent_key']
        running_key = sent_state['running_key']
        finished_key = sent_state['finished_key']

        col1, col2 = st.columns([1, 3])
        
        with col1:
            if not st.session_state[sent_key]:
                if st.button("🚀 Send to Opentrons", key=f"send_{hash(code)}"):
                    # Send to Flex via HTTP API
                    try:
                        import requests
                        from utils.io_helpers import save_protocol

                        path = save_protocol(code, filename="generated_protocol.py")
                        resp = requests.post(
                            "http://localhost:8000/send_to_flex",
                            json={"filepath": path}
                        )
                        if resp.status_code == 200:
                            st.session_state[sent_key] = True
                            st.session_state[running_key] = True
                            st.success("Protocol sent to Opentrons!")
                        else:
                            st.error(f"Failed to send protocol: {resp.text}")
                    except Exception as e:
                        st.error(f"Error sending to Opentrons Flex: {e}")
                    st.rerun()
        
        with col2:
            if st.button("📥 Download Protocol", key=f"download_{hash(code)}"):
                st.download_button(
                    label="💾 Save as .py file",
                    data=code,
                    file_name="protocol.py",
                    mime="text/x-python"
                )

        if st.session_state[sent_key] and st.session_state[running_key] and not st.session_state[finished_key]:
            with st.spinner("Experiment is running on Opentrons..."):
                import time
                progress_bar = st.progress(0, text="Running protocol...")
                for percent in range(0, 101, 10):
                    progress_bar.progress(percent, text=f"Running protocol... {percent}%")
                    time.sleep(0.15)
                st.session_state[running_key] = False
                st.session_state[finished_key] = True
                st.rerun()
        elif st.session_state[finished_key]:
            st.success("✅ Experiment completed!")
            if st.button("🔄 Start new experiment", key=f"reset_{hash(code)}"):
                # Reset chat and protocol state
                st.session_state['chat_history'] = []
                for k in [sent_key, running_key, finished_key]:
                    st.session_state.pop(k, None)
                st.rerun()

def render_simulation_status(stderr, experiment_type=None):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("**🔍 Protocol Validation:**")
        
        if not stderr:
            st.success("✅ Protocol simulation succeeded. No errors detected.")
            st.markdown("*The protocol is ready for execution on the Opentrons Flex.*")
        else:
            st.error("❌ Protocol simulation failed.")
            
            # error analysis
            error_analysis = analyze_error(stderr)
            
            with st.expander("🔍 Error Details", expanded=True):
                st.code(stderr, language="text")
            
            with st.expander("💡 Suggested Fixes"):
                for fix in error_analysis:
                    st.markdown(f"• {fix}")

def analyze_error(stderr: str) -> list[str]:
    """Provide more detailed error analysis and suggestions."""
    suggestions = []
    
    if "KeyError" in stderr:
        suggestions.append("Missing required parameter in protocol")
        suggestions.append("Check that all labware and reagents are properly defined")
    
    if "OutOfTipsError" in stderr:
        suggestions.append("Not enough tips for the protocol")
        suggestions.append("Add more tip racks or optimize tip usage")
    
    if "SlotDoesNotExistError" in stderr:
        suggestions.append("Invalid deck slot specified")
        suggestions.append("Use valid deck slots (A1-D4 for Flex)")
    
    if "ModuleNotFoundError" in stderr:
        suggestions.append("Missing required module or incorrect import")
        suggestions.append("Check that all required packages are installed")
    
    if "IncompatibleLabwareError" in stderr:
        suggestions.append("Labware not compatible with selected pipette")
        suggestions.append("Check pipette and labware compatibility")
    
    if not suggestions:
        suggestions.append("Unknown error - please review protocol code")
        suggestions.append("Check Opentrons documentation for troubleshooting")
    
    return suggestions

def get_experiment_type_from_prompt(prompt: str) -> str:
    """Extract experiment type from user prompt for UI enhancements."""
    prompt_lower = prompt.lower()
    
    if "serial dilution" in prompt_lower:
        return "serial_dilution"
    elif any(term in prompt_lower for term in ["pcr", "amplification"]):
        return "pcr_setup"
    elif any(term in prompt_lower for term in ["wash", "washing"]):
        return "plate_washing"
    elif any(term in prompt_lower for term in ["transfer", "move"]):
        return "sample_transfer"
    elif any(term in prompt_lower for term in ["cell", "culture"]):
        return "cell_culture"
    elif any(term in prompt_lower for term in ["enzyme", "assay"]):
        return "enzyme_assay"
    else:
        return "generic"

# --- Sidebar for experiment templates ---
def render_sidebar():
    st.sidebar.title("🧪 Quick Templates")
    st.sidebar.markdown("Click to use a template:")
    
    templates = {
        "Serial Dilution": "Run a 5-step 1:2 serial dilution with 100µL starting volume",
        "PCR Setup": "Set up PCR reactions for 24 samples with 25µL reaction volume",
        "Plate Washing": "Wash 96 wells with 200µL wash buffer, 3 cycles",
        "Sample Transfer": "Transfer 50µL from 48 source wells to destination plate",
        "Cell Culture": "Seed cells in 24 wells with 150µL media and 50µL cell suspension",
        "Enzyme Assay": "Set up enzyme assay for 48 samples with 100µL total volume"
    }
    
    for name, template in templates.items():
        if st.sidebar.button(f"📋 {name}", key=f"template_{name}"):
            st.session_state['pending_message'] = template
            st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 Tips")
    st.sidebar.markdown("""
    - Specify volumes in µL (e.g., "100µL")
    - Mention number of samples
    - Include dilution factors for serial dilutions
    - Specify plate types if needed
    """)

# --- Chat State ---
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = 'cornucopia_chat'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# --- Main App Layout ---
st.set_page_config(
    page_title="🔬 CornucopiaV2",
    page_icon="🧬",
    layout="wide"
)

# Header
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.title("🔬 CornucopiaV2")
    st.markdown("*AI-Powered Lab Automation for Opentrons Flex*")

# Sidebar
render_sidebar()

# Main chat area
chat_container = st.container()

# --- Chat Input Control ---
disable_input = False
for msg in st.session_state['chat_history']:
    if msg.get('protocol_code'):
        code = msg['content']
        sent_key = f"sent_{hash(code)}"
        running_key = f"running_{hash(code)}"
        finished_key = f"finished_{hash(code)}"
        if st.session_state.get(running_key, False) or st.session_state.get(finished_key, False):
            disable_input = True

with chat_container:
    if disable_input:
        st.chat_input("Chat disabled while experiment is running.", key="chat_input", disabled=True)
    else:
        user_input = st.chat_input("Describe your experiment...", key="chat_input")
        if user_input:
            st.session_state['pending_message'] = user_input
            st.rerun()

# --- Process pending messages ---
if 'pending_message' in st.session_state:
    pending = st.session_state.pop('pending_message')
    experiment_type = get_experiment_type_from_prompt(pending)
    
    st.session_state['chat_history'].append({
        'role': 'user', 
        'content': pending,
        'experiment_type': experiment_type
    })
    
    with st.spinner("Processing your request..."):
        try:
            # Step 1: Prompt clarification
            clarify_result = Runner.run_sync(PromptCreatorAgent, pending)
            clarified = json.loads(clarify_result.final_output)
            confirmation = clarified["confirmation"]
            clean_prompt = clarified["clean_prompt"]
            
            st.session_state['chat_history'].append({
                'role': 'assistant', 
                'content': confirmation, 
                'clarification': True,
                'experiment_type': experiment_type
            })

            # Only run protocol generator if clean_prompt exists
            if not clean_prompt:
                st.warning("Please provide more details about your experiment.")
                st.session_state['chat_history'].append({
                    'role': 'assistant', 
                    'content': "Please provide more details about your experiment."
                })
            else:
                # Step 2: Protocol generation
                protocol_result = Runner.run_sync(ProtocolGeneratorAgent, clean_prompt)
                agent_reply = protocol_result.final_output.strip()
                
                # Step 3: Show protocol code if generated
                if "protocol.load_instrument" in agent_reply or "pipette" in agent_reply:
                    def indent(code: str, spaces: int = 4) -> str:
                        pad = " " * spaces
                        return "\n".join(pad + line if line.strip() != "" else "" for line in code.splitlines())
                    
                    full_protocol = get_fixed_header().rstrip() + "\n" + indent(agent_reply)
                    
                    # Track protocol send state in session
                    sent_key = f"sent_{hash(full_protocol)}"
                    running_key = f"running_{hash(full_protocol)}"
                    finished_key = f"finished_{hash(full_protocol)}"
                    
                    for k in [sent_key, running_key, finished_key]:
                        if k not in st.session_state:
                            st.session_state[k] = False
                    
                    st.session_state['chat_history'].append({
                        'role': 'assistant',
                        'content': full_protocol,
                        'protocol_code': True,
                        'sent_key': sent_key,
                        'running_key': running_key,
                        'finished_key': finished_key,
                        'experiment_type': experiment_type
                    })
                    
                    # Save and QC
                    path = save_protocol(full_protocol)
                    stderr = _simulate_protocol(path)
                    st.session_state['chat_history'].append({
                        'role': 'assistant', 
                        'content': stderr, 
                        'qc': True,
                        'experiment_type': experiment_type
                    })
                else:
                    st.error("Failed to generate valid protocol code.")
                    st.session_state['chat_history'].append({
                        'role': 'assistant',
                        'content': f"I had trouble generating the protocol. Here's what I got: {agent_reply}"
                    })
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.session_state['chat_history'].append({
                'role': 'assistant',
                'content': f"Sorry, I encountered an error: {str(e)}"
            })

# --- Render Chat History ---
with chat_container:
    for idx, msg in enumerate(st.session_state['chat_history']):
        experiment_type = msg.get('experiment_type')
        
        if msg.get('clarification'):
            render_clarification(msg['content'], experiment_type)
        elif msg.get('protocol_code'):
            render_protocol(msg['content'], msg, experiment_type)
        elif msg.get('qc'):
            render_simulation_status(msg['content'], experiment_type)
        else:
            render_chat(msg['role'], msg['content'])

# --- Footer ---
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Supported Experiments:**")
    st.markdown("• Serial Dilutions\n• PCR Setup\n• Plate Washing")
with col2:
    st.markdown("**Features:**")
    st.markdown("• AI Protocol Generation\n• Simulation & QC\n• Direct Opentrons Integration")
with col3:
    st.markdown("**Status:**")
    if st.session_state.get('chat_history'):
        st.markdown("🟢 Ready")
    else:
        st.markdown("🔵 Waiting for input")