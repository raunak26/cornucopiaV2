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
set_default_openai_client(client)

ensure_event_loop()

# --- UI Helper Functions ---
def render_chat(role, message):
    avatar = "🧑" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message)

def render_clarification(confirmation):
    with st.container():
        st.markdown("**🤖 Clarification:**")
        st.info(confirmation)

def render_protocol(code):
    with st.container():
        st.markdown("**🧬 Generated Protocol:**")
        st.code(code, language="python")

def render_simulation_status(stderr):
    with st.container():
        if not stderr:
            st.success("✅ Protocol simulation succeeded. No errors detected.")
        else:
            st.error("❌ Protocol simulation failed.")
            st.warning(f"QC Agent says: {_extract_missing(stderr)}")

# --- Chat State ---
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = 'cornucopia_chat'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.title("🔬 Cornucopia (Conversational Agent)")

user_input = st.chat_input("Describe your experiment or answer the agent's question...", key="chat_input")

if user_input:
    st.session_state['pending_message'] = user_input
    st.rerun()

if 'pending_message' in st.session_state:
    pending = st.session_state.pop('pending_message')
    st.session_state['chat_history'].append({'role': 'user', 'content': pending})
    with st.spinner("Thinking..."):
        # Step 1: Prompt clarification
        clarify_result = Runner.run_sync(PromptCreatorAgent, pending)
        clarified = json.loads(clarify_result.final_output)
        confirmation = clarified["confirmation"]
        clean_prompt = clarified["clean_prompt"]
        st.session_state['chat_history'].append({'role': 'assistant', 'content': confirmation, 'clarification': True})

        # Only run protocol generator if clean_prompt exists
        if not clean_prompt:
            st.warning("Please describe your experiment (e.g., 'run a serial dilution').")
            st.session_state['chat_history'].append({'role': 'assistant', 'content': "Please describe your experiment (e.g., 'run a serial dilution')."})
        else:
            # Step 2: Protocol generation
            protocol_result = Runner.run_sync(ProtocolGeneratorAgent, clean_prompt)
            agent_reply = protocol_result.final_output.strip()
            st.session_state['chat_history'].append({'role': 'assistant', 'content': agent_reply, 'protocol': True})
            # Step 3: Show protocol code if generated
            if "protocol.load_instrument" in agent_reply and "for well in" in agent_reply:
                def indent(code: str, spaces: int = 4) -> str:
                    pad = " " * spaces
                    return "\n".join(pad + line if line.strip() != "" else "" for line in code.splitlines())
                full_protocol = get_fixed_header().rstrip() + "\n" + indent(agent_reply)
                st.session_state['chat_history'].append({'role': 'assistant', 'content': full_protocol, 'protocol_code': True})
                # Save and QC
                path = save_protocol(full_protocol)
                stderr = _simulate_protocol(path)
                st.session_state['chat_history'].append({'role': 'assistant', 'content': stderr, 'qc': True})

# --- Render Chat History ---
for msg in st.session_state['chat_history']:
    if msg.get('clarification'):
        render_clarification(msg['content'])
    elif msg.get('protocol_code'):
        render_protocol(msg['content'])
    elif msg.get('qc'):
        render_simulation_status(msg['content'])
    else:
        render_chat(msg['role'], msg['content'])
