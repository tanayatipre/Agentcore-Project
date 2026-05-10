import csv
import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_core.tools import tool

from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

from langchain_groq import ChatGroq
from langchain.agents import create_agent

load_dotenv()

# Load FAQ CSV

def load_faq_csv(path: str) -> List[Document]:
    docs = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            q = row["question"].strip()
            a = row["answer"].strip()

            docs.append(
                Document(
                    page_content=f"Q: {q}\nA: {a}"
                )
            )

    return docs


# Load FAISS vectorstore

@lru_cache
def get_vectorstore():
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name="us-east-1"
    )

    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vectorstore


# Tool 1

@tool
def search_faq(query: str) -> str:
    """
    Search the FAQ knowledge base for relevant information.

    Args:
        query: User question

    Returns:
        Relevant FAQ entries
    """

    store = get_vectorstore()

    results = store.similarity_search(query, k=3)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} relevant FAQ entries:\n\n{context}"


# Tool 2

@tool
def search_detailed_faq(query: str, num_results: int = 5) -> str:
    """
    Search FAQ knowledge base with more results.

    Args:
        query: User question
        num_results: Number of results

    Returns:
        Detailed FAQ entries
    """

    store = get_vectorstore()

    results = store.similarity_search(query, k=num_results)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} detailed FAQ entries:\n\n{context}"


# Tool 3

@tool
def reformulate_query(original_query: str, focus_aspect: str) -> str:
    """
    Reformulate query for a specific aspect and search again.

    Args:
        original_query: Original user question
        focus_aspect: Specific angle to search

    Returns:
        Reformulated search results
    """

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


# Tool list

tools = [
    search_faq,
    search_detailed_faq,
    reformulate_query
]


# LLM

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)


# System prompt

system_prompt = """
You are a helpful FAQ assistant with access to a knowledge base.

Your goal is to answer user questions accurately using the available tools.

Guidelines:
1. Start by using the search_faq tool
2. If needed, use search_detailed_faq
3. Use reformulate_query for complex queries
4. Combine information from multiple searches
5. Keep responses clear and concise
6. If no information is found, clearly say so
"""


# Create agent

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt
)


# Run locally

if __name__ == "__main__":

    result = agent.invoke({
        "messages": [
            ("human", "Explain roaming activation.")
        ]
    })

    print(result["messages"][-1].content)