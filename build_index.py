import csv
import os
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

import certifi
import ssl
import time
import traceback

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

    chunks = docs
    print(f"Using {len(chunks)} chunks (1 per FAQ)")

    bedrock_region = os.getenv("BEDROCK_REGION", "us-east-1")
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=bedrock_region
    )

    print("Creating FAISS index...")

    texts = [doc.page_content for doc in chunks]
    metadatas = [doc.metadata for doc in chunks]
    all_embeddings = []

    print(f"Embedding {len(texts)} documents sequentially to respect AWS rate limits...")
    for i, text in enumerate(texts):
        for attempt in range(5):
            try:
                emb = embeddings.embed_query(text)
                all_embeddings.append(emb)
                break
            except Exception as e:
                time.sleep(2 + attempt)
        else:
            raise Exception(f"Failed to embed document {i} after 5 retries.")
            
        if i % 100 == 0 and i > 0:
            print(f"Progress: {i}/{len(texts)}", end="\\r")

    print(f"\\nFinished generating {len(all_embeddings)} embeddings. Building FAISS vectorstore...")
    text_embedding_pairs = list(zip(texts, all_embeddings))
    vectorstore = FAISS.from_embeddings(text_embedding_pairs, embeddings, metadatas=metadatas)

    # save locally
    vectorstore.save_local("./faiss_index")

    print("FAISS index saved to ./faiss_index")

if __name__ == "__main__":
    main()