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

import os
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


if 'session_id' not in st.session_state:
    st.session_state['session_id'] = 'cornucopia_chat'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# --- Chat input and immediate display logic ---
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
        st.write('PromptCreatorAgent output:', clarify_result.final_output)  # Debug output
        st.code(clarify_result.final_output, language="json")
        clarified = json.loads(clarify_result.final_output)
        confirmation = clarified["confirmation"]
        clean_prompt = clarified["clean_prompt"]
        st.session_state['chat_history'].append({'role': 'assistant', 'content': confirmation})

        # Step 2: Protocol generation
        protocol_result = Runner.run_sync(ProtocolGeneratorAgent, clean_prompt)
        agent_reply = protocol_result.final_output.strip()
        st.session_state['chat_history'].append({'role': 'assistant', 'content': agent_reply})
        # Step 3: Show protocol code if generated
        if "protocol.load_instrument" in agent_reply and "for well in" in agent_reply:
            def indent(code: str, spaces: int = 4) -> str:
                pad = " " * spaces
                return "\n".join(pad + line if line.strip() != "" else "" for line in code.splitlines())

            full_protocol = get_fixed_header().rstrip() + "\n" + indent(agent_reply)
            st.subheader("🧬 Generated Protocol")
            st.code(full_protocol, language="python")
            # Save and QC
            path = save_protocol(full_protocol)
            stderr = _simulate_protocol(path)
            if not stderr:
                st.success("✅ Protocol simulation succeeded.")
            else:
                st.error("❌ Simulation failed.")
                st.warning(f"QC Agent says: {_extract_missing(stderr)}")

for msg in st.session_state['chat_history']:
    if msg['role'] == 'user':
        st.chat_message("user").write(msg['content'])
    else:
        st.chat_message("assistant").write(msg['content'])
