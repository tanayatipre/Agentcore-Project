import os
from functools import lru_cache

from langchain_core.tools import tool

from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

from langchain_groq import ChatGroq

from dotenv import load_dotenv
from langchain.agents import create_agent

# Import AgentCore runtime
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Create the AgentCore app instance
app = BedrockAgentCoreApp()

# Load env
load_dotenv()

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load FAISS Index

@lru_cache
def get_vectorstore():
    print("Loading embeddings...")

    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name="us-east-1"
    )

    print("Loading FAISS index...")

    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    print("FAISS loaded")

    return vectorstore


# Tools (RAG-based)

@tool
def search_faq(query: str) -> str:
    """Search FAQ data using semantic similarity."""

    store = get_vectorstore()

    results = store.similarity_search(query, k=3)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} relevant FAQ entries:\n\n{context}"


@tool
def search_detailed_faq(query: str, num_results: int = 5) -> str:
    """Search FAQ with more results."""

    store = get_vectorstore()

    results = store.similarity_search(query, k=num_results)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} detailed FAQ entries:\n\n{context}"


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


tools = [
    search_faq,
    search_detailed_faq,
    reformulate_query
]

# LLM

model = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=GROQ_API_KEY
)

# System Prompt

system_prompt = """
You are a helpful FAQ assistant with access to a knowledge base.

Your goal is to answer user questions accurately using the available tools.

Guidelines:
1. Start by using the search_faq tool to find relevant information
2. If the initial search doesn't provide enough info, use search_detailed_faq for more results
3. If the query is complex, use reformulate_query to search different aspects
4. Synthesize information from multiple tool calls if needed
5. Always provide a clear, concise answer based on the retrieved information
6. If you cannot find relevant information, clearly state that

Think step-by-step and use tools strategically to provide the best answer.
"""

# Create Agent

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt
)

# AgentCore Entrypoint

@app.entrypoint
def agent_invocation(payload, context):
    """Handler for agent invocation in AgentCore runtime."""

    print("Received payload:", payload)
    print("Context:", context)

    # Extract query from payload
    query = payload.get("prompt", "")

    # Invoke the agent
    result = agent.invoke(
        {
            "messages": [
                ("human", query)
            ]
        }
    )

    print("Result:", result)

    messages = result.get("messages", [])

    answer = (
        messages[-1].content
        if messages
        else "No response generated"
    )

    return {
        "result": answer
    }


if __name__ == "__main__":
    print("Starting app...")
    app.run()