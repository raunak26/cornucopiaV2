# 🧬 CornucopiaV2: Modular Agent-Based Lab Automation for Opentrons Flex

CornucopiaV2 is a modular, agent-driven platform for generating, validating, and simulating Opentrons Flex protocols using natural language and the OpenAI Agents SDK. It features a conversational Streamlit UI, robust protocol generation, and automated QC via simulation.

---

## 🚦 Agent Pipeline

The system is built around a chain of specialized agents:

1. **PromptCreatorAgent**: Clarifies vague user requests (e.g., "run a serial dilution") into structured, Opentrons-ready prompts.
2. **ProtocolGeneratorAgent**: Generates Python code for the Opentrons `run(protocol)` function based on the clarified prompt.
3. **QCAgent**: Simulates the generated protocol using `opentrons_simulate`, extracts errors, and provides actionable feedback.

---

## 💡 Example Workflow

```text
User says: "can you run a serial dilution?"
→ PromptCreatorAgent: clarifies prompt to structured intent
→ ProtocolGeneratorAgent: writes Opentrons run() logic
→ QCAgent: simulates using `opentrons_simulate`, catches errors
→ UI: Renders protocol, reports missing variables or OutOfTips errors
```

---

## 🖥️ Usage

- Launch the Streamlit UI: chat with the agent, describe your experiment, and receive a validated, simulated protocol.
- The app will:
  - Clarify your intent
  - Generate protocol code
  - Simulate and QC the protocol
  - Display errors or success

---

## 📁 Directory Structure

```
cornucopiaV2/
├── app.py                  # (legacy, see main.py)
├── main.py                 # Main Streamlit app (agent pipeline)
├── create_index.py         # RAG index generation script
├── convert_to_markdown.py  # Converts docs to plain text or markdown
├── requirements.txt        # Python dependencies
├── .env                    # API keys (excluded from Git)
├── .gitignore              # Ignore rules
├── cornucopia_agents/      # Modular agent definitions (OpenAI Agents SDK)
├── utils/                  # I/O, validation, and header helpers
├── data/                   # Markdown docs for vectorization
├── generated/              # Protocols generated for simulation
├── index/                  # LlamaIndex vector store
├── test_files/             # Protocol test variants
└── ...
```

---

## 🛠️ Installation & Setup

1. **Clone the Repository**
    ```bash
    git clone https://github.com/raunak26/cornucopiaV2.git
    cd cornucopiaV2
    ```
2. **Create and Activate a Virtual Environment**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate   # macOS/Linux
    # OR
    .venv\Scripts\activate      # Windows
    ```
3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
4. **Set Up Environment Variables**
    - Create a `.env` file in the root directory:
      ```env
      OPENAI_API_KEY=sk-...
      ```
    - Do **not** commit this file — it's ignored by `.gitignore`.
5. **Create the Vector Index (for RAG)**
    ```bash
    python create_index.py
    ```
    - Place docs in `data/` before running.
6. **Run the App**
    ```bash
    streamlit run main.py
    ```

---

## 🧑‍💻 Development & Contributing

- Modular agent code in `cornucopia_agents/` (see local README)
- Utility helpers in `utils/`
- Test protocol variants in `test_files/`
- Use `black .` and `flake8 .` for formatting/linting
- PRs and issues welcome!

---

## 🚧 Future Goals

- LLM-powered error correction and auto-filling of missing parameters
- More advanced protocol templates and multi-step workflows
- Integration with Opentrons API for direct robot execution
- Enhanced RAG with richer documentation and context

---

## 🗂️ Folder Guide

- `cornucopia_agents/` — Modular agents (PromptCreatorAgent, ProtocolGeneratorAgent, QCAgent)
- `utils/` — I/O, validation, and protocol header helpers
- `data/` — Markdown docs for vectorization (Opentrons 2.19 reference)
- `generated/` — Protocols generated for simulation and QC
- `index/` — LlamaIndex vector store cache
- `test_files/` — Protocol test variants (e.g., thisworks.py)
- `agents/` — **Deprecated** (migrated to `cornucopia_agents/`)

---