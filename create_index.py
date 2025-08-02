import os
from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.workflow import Context  # For chat memory
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.settings import Settings

from openai import OpenAI as OpenAIClient


# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Register embedding model
Settings.embed_model = OpenAIEmbedding(
    model_name="text-embedding-ada-002",
    client=client,
)

def create_index(data_path: str, data_file: str, index_name: str):
    persist_dir = os.path.join("index", index_name)
    file_path = os.path.join(data_path, data_file)

    if not os.path.exists(persist_dir):
        print("🔧 Creating new index...")
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=persist_dir)
        return index
    else:
        print("✅ Using existing index.")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        return load_index_from_storage(storage_context)

if __name__ == "__main__":
    index = create_index("data", "python_api_219_docs.md", "v219_ref")
    query_engine = index.as_query_engine()
    while True:
        query = input("Ask a question: ")
        print(query_engine.query(query))
