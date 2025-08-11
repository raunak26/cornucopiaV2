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
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("**🤖 Clarification:**")
        st.info(confirmation)

def render_protocol(code, sent_state):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("**🧬 Generated Protocol:**")
        st.code(code, language="python")
        # --- Send to Opentrons Button & State ---
        sent_key = sent_state['sent_key']
        running_key = sent_state['running_key']
        finished_key = sent_state['finished_key']

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
                    else:
                        st.error(f"Failed to send protocol: {resp.text}")
                except Exception as e:
                    st.error(f"Error sending to Opentrons Flex: {e}")
                st.rerun()

        elif st.session_state[running_key] and not st.session_state[finished_key]:
            with st.spinner("Experiment is running on Opentrons..."):
                import time
                for percent in range(0, 101, 10):
                    st.progress(percent, text="Running protocol...")
                    time.sleep(0.15)
                st.session_state[running_key] = False
                st.session_state[finished_key] = True
                st.rerun()
        elif st.session_state[finished_key]:
            st.success("✅ Experiment launched!")
            if st.button("Start another run", key=f"reset_{hash(code)}"):
                # Reset chat and protocol state
                st.session_state['chat_history'] = []
                for k in [sent_key, running_key, finished_key]:
                    st.session_state.pop(k, None)
                st.experimental_rerun()
            st.markdown(
                "<div style='color:gray; font-style:italic;'>Chat input disabled while experiment is running.</div>",
                unsafe_allow_html=True
            )

def render_simulation_status(stderr):
    with st.chat_message("assistant", avatar="🤖"):
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

st.title("🔬 Cornucopia")

# --- Chat Input Control ---
# Grey out/hide chat input if experiment is running or finished
disable_input = False
for msg in st.session_state['chat_history']:
    if msg.get('protocol_code'):
        code = msg['content']
        sent_key = f"sent_{hash(code)}"
        running_key = f"running_{hash(code)}"
        finished_key = f"finished_{hash(code)}"
        if st.session_state.get(running_key, False) or st.session_state.get(finished_key, False):
            disable_input = True

if disable_input:
    st.chat_input("Chat disabled while experiment is running.", key="chat_input", disabled=True)
else:
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
            # Step 3: Show protocol code if generated
            if "protocol.load_instrument" in agent_reply and "for well in" in agent_reply:
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
                    'finished_key': finished_key
                })
                # Save and QC
                path = save_protocol(full_protocol)
                stderr = _simulate_protocol(path)
                st.session_state['chat_history'].append({'role': 'assistant', 'content': stderr, 'qc': True})

# --- Render Chat History ---
for idx, msg in enumerate(st.session_state['chat_history']):
    # Collapse old chat history for tidiness (optional)
    with st.expander(f"Step {idx+1}: {msg.get('role','system').capitalize()} message", expanded=(idx >= len(st.session_state['chat_history'])-3)):
        if msg.get('clarification'):
            render_clarification(msg['content'])
        elif msg.get('protocol_code'):
            render_protocol(msg['content'], msg)
        elif msg.get('qc'):
            render_simulation_status(msg['content'])
        else:
            render_chat(msg['role'], msg['content'])