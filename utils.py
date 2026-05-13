import os
import csv
from functools import lru_cache
from typing import List

from langchain_core.documents import Document
from langchain_core.tools import tool

from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

@lru_cache
def get_vectorstore():
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    
    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
    
    return vectorstore

@tool
def search_faq(query: str, num_results: int = 3) -> str:
    """Search FAQ data using semantic similarity."""
    store = get_vectorstore()
    results = store.similarity_search(query, k=num_results)

    if not results:
        return "No relevant FAQ entries found."
    
    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])
    return f"Found {len(results)} relevant FAQ entries:\n\n{context}"

@tool
def reformulate_query(original_query: str, focus_aspect: str) -> str:
    """Reformulate query for a specific aspect and search."""
    store = get_vectorstore()
    reformulated = f"{focus_aspect} related to {original_query}"
    results = store.similarity_search(reformulated, k=3)

    if not results:
        return f"No results found for aspect: {focus_aspect}"

    context = "\n\n---\n\n".join([
        f"Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])
    return f"Results for '{focus_aspect}' aspect:\n\n{context}"

tools = [search_faq, reformulate_query]

def load_faq_csv(path: str) -> List[Document]:
    docs = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
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
