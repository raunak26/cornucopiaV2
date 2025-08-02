# app.py

import streamlit as st
from llama_index.core import StorageContext, load_index_from_storage
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Load index
storage_context = StorageContext.from_defaults(persist_dir="index/v219_ref")
index = load_index_from_storage(storage_context)
query_engine = index.as_query_engine()

# Set up OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# UI
st.title("🔬 Opentrons AI Assistant")
prompt = st.text_area("Describe your experiment:", height=150)
submit = st.button("Generate Protocol")

if submit and prompt.strip():
    with st.spinner("Thinking..."):
        # Step 1: Retrieve context
        retrieved_docs = query_engine.query(prompt).response

        # Step 2: Call OpenAI
        system_prompt = "You're an expert at generating Opentrons Python protocols."
        full_prompt = f"{system_prompt}\n\nUser prompt: {prompt}\n\nRelevant Docs:\n{retrieved_docs}"

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.4,
        )

        st.code(response.choices[0].message.content, language="python")
