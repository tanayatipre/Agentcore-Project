import csv
import os
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

import certifi
import ssl
import time
import traceback

# Ensure Python and other libraries use certifi's CA bundle for HTTPS
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["CURL_CA_BUNDLE"] = certifi.where()

# Load CSV

def load_faq_csv(path: str) -> List[Document]:
    docs = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        print("Columns:", reader.fieldnames)

        for row in reader:
            q = row.get("Question") or row.get("question")
            a = row.get("Answer") or row.get("answer")

            if not q or not a:
                continue

            docs.append(
                Document(
                    page_content=f"Q: {q.strip()}\nA: {a.strip()}"
                )
            )
    return docs

# Main

def main():
    print('Loading CSV...')
    docs = load_faq_csv("./jio_faq.csv")
    
    print(f"Loaded {len(docs)} documents")

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    # Embeddings: create with simple retry to surface SSL/client errors clearly
    embeddings = None
    last_exc = None
    for attempt in range(3):
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5"
            )
            break
        except Exception as e:
            last_exc = e
            print(f"Attempt {attempt+1} to create embeddings failed: {e}")
            traceback.print_exc()
            time.sleep(1 + attempt * 2)

    if embeddings is None:
        print("Failed to create HuggingFaceEmbeddings after retries.")
        raise last_exc

    print("Creating FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # save locally
    vectorstore.save_local("./faiss_index")

    print("FAISS index saved to ./faiss_index")

if __name__ == "__main__":
    main()