import os
import uuid
from functools import lru_cache
from typing import List

from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

from langgraph.store.base import BaseStore

# FAISS + HF Embeddings
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# Agentcore
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore
from langchain.agents.middleware import AgentMiddleware, AgentState

from dotenv import load_dotenv
_ = load_dotenv()

app = BedrockAgentCoreApp()

# Config
Region = "us-east-1"
MEMORY_ID = "customer_care_agent_memory-369OL1GRbv"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Load FAISS Index (precomputed)

@lru_cache
def get_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5"
    )

    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )

    return vectorstore

# Tools (Rag-based)

@tool
def search_faq(query: str) -> str:
    """Search FAQ data using semantic similarity."""
    store = get_vectorstore()
    results = store.similarity_search(query,k=3)

    if not results:
        return "No relevant FAQ entries found."
    
    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])
    return f"Found {len(results)} relevant FAQ entries: \n\n{context}"

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
def reformulate_query(original_query: str, focus_aspec: str) -> str:
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

    return f"Results for '{focus_aspect}'
aspect:\n\n{context}"

tools = [search_faq, search_detailed_faq, reformulate_query]

# Memory Middleware

class MemoryMiddleware(AgentMiddleware):
    def pre_model_hook(self, state: AgentState, config: RunnableConfig, *, store: BaseStore):
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]

        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        # fetch recent memory 
        past = store.search(namespace, query="", limit=5)
        history = [item.value["message"] for item in past if "message" in item.value]

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break
        return {"messages": history + messages}
    
    def post_model_hook(self, state: config: RunnableConfig, *, store: BaseStore):
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]
        
        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break
        return state

# LLM + Agent

@lru_cache
def get_llm():
    return init_chat_model(
        model="openai/gpt-oss-20b",
        model_provider="groq",
        api_key=GROQ_API_KEY
    )

@lru_cache
def get_agent():
    checkpointer = AgentCoreMemorySaver(memory_id=MEMORY_ID)
    store = AgentCoreMemoryStore(memory_id=MEMORY_ID)

    return create_agent(
        model=get_llm(),
        tools=tools,
        checkpointer=checkpointer,
        store=store,
        middleware=[MemoryMiddleware()]
        system_prompt="""you are a helpful FAQ assistant with memory.
    
    Use tools to answer questions.
    Always rely on retrieved FAQ data.
    Be clear, concise, and accurate.""",
    )


# Entrypoint

@app.entrypoint
def agent_invocation(payload, context):
    query = payload.get("prompt", "")

    actor_id = payload.get("actor_id", "default-user")
    thread_id = payload.get("thread_id", "default-session")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id
        }
    }

    agent = get_agent()

    result = agent.invoke(
        {"messages": [("human", query)]},
        config=config
    )

    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "No response"

    return {
        "result": answer,
        "actor_id": actor_id,
        "thread_id": thread_id
    }

if __name__ == "__main__":
    app.run()