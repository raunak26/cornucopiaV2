# app.py

import streamlit as st
from llama_index.core import StorageContext, load_index_from_storage
from openai import OpenAI
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load vector index
storage_context = StorageContext.from_defaults(persist_dir="index/v219_ref")
index = load_index_from_storage(storage_context)
query_engine = index.as_query_engine()

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# UI layout
st.title("🔬 Cornucopia")
prompt = st.text_area("Describe your experiment:", height=150)
generate = st.button("Generate Protocol")

code_output = ""

if generate and prompt.strip():
    with st.spinner("Thinking..."):
        # Step 1: Retrieve relevant documentation
        retrieved_docs = query_engine.query(prompt).response

        # Step 2: Compose strict system prompt
        system_prompt = (
            "You are an expert in writing Opentrons Flex Python protocols using only API level 2.12. "
            "You must generate Python code only — no explanations, no comments, and no extra text. "
            "Assume exactly two pipettes are available: one 8-channel 50µL pipette and one 8-channel 1000µL pipette. "
            "Use the retrieved context strictly. The output must be a valid, executable Opentrons protocol for the Flex. "
            "Do not include metadata explanations or any non-code content."
        )

        # Step 3: Create full prompt
        full_prompt = f"{system_prompt}\n\nUser prompt: {prompt}\n\nRelevant Docs:\n{retrieved_docs}"

        # Step 4: Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.4,
        )

        code_output = response.choices[0].message.content

# Display results if code was generated
if code_output:
    st.subheader("🧬 Generated Protocol")
    st.code(code_output, language="python")

    # Show simulation progress bar
    st.subheader("🧪 Simulating Protocol")
    progress_bar = st.progress(0)
    for percent_complete in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(percent_complete)

    time.sleep(1)  # Delay for UX effect
    st.success("✅ SUCCESS: Protocol validated")

    # Upload to robot (placeholder)
if st.button("🚀 Send to Opentrons"):
    with st.spinner("Uploading to robot... Please wait."):
        time.sleep(5)  # Simulate upload time
    st.success("📤 Protocol uploaded to Opentrons Flex!")
