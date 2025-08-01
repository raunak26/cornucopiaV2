## 🛠️ Installation & Setup

Follow these steps to get started with Cornucopia:

### 1. Clone the Repository

```bash
git clone https://github.com/raunak26/cornucopiaV2.git
cd cornucopiaV2
```

---

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# OR
.venv\Scripts\activate      # Windows
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-...
```

> ⚠️ Do **not** commit this file — it's ignored by `.gitignore` to protect your secrets.

---

### 5. Create the Vector Index (for RAG)

This step indexes your Opentrons documentation or other data for retrieval-augmented generation (RAG).

```bash
python create_index.py
```

> Ensure your data is placed inside the `data/` folder before running this command.  
> The index will be saved and used to power LLM queries.

---

### 6. Run the App

```bash
python app.py
```

This launches the RAG interface that uses your vector index and LLM to answer questions based on your documentation.

---

### ✅ Optional: Format & Lint Code

```bash
black .
flake8 .
```

---

### 📁 File Structure

```
cornucopiaV2/
├── .venv/                  # Virtual environment (ignored)
├── app.py                  # Main app entry point
├── create_index.py         # RAG index generation script
├── convert_to_markdown.py  # Converts docs to plain text or markdown
├── data/                   # Source documentation files
├── requirements.txt        # Python dependencies
├── .env                    # API keys (excluded from Git)
├── .gitignore              # Ignore rules
```