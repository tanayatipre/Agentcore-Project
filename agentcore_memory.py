import os
import argparse
import uuid
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

from langgraph.store.base import BaseStore

# FAISS + HF Embeddings
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings

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

import boto3
def get_groq_api_key():
    local_key = os.getenv("GROQ_API_KEY")
    if local_key:
        return local_key
    try:
        ssm = boto3.client('ssm', region_name=Region)
        response = ssm.get_parameter(Name='/agentcore/GROQ_API_KEY', WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Failed to fetch GROQ_API_KEY from SSM: {e}")
        return None

GROQ_API_KEY = get_groq_api_key()

print("Starting app...")

# Load FAISS Index (precomputed)

@lru_cache
def get_vectorstore():
    print("Loading embeddings...")
    embeddings = BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=Region
    )
    print("Loading FAISS index...")

    vectorstore = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("FAISS loaded")
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
    
tools = [search_faq, search_detailed_faq, reformulate_query]

# Memory Middleware

def clear_namespace_memory(store: BaseStore, namespace: tuple[str, ...]) -> int:
    deleted = 0
    while True:
        items = store.search(namespace, query="", limit=100, offset=0)
        if not items:
            break
        for item in items:
            store.delete(namespace, item.key)
        deleted += len(items)
    return deleted

class MemoryMiddleware(AgentMiddleware):
    def pre_model_hook(self, state: AgentState, config: RunnableConfig, *, store: BaseStore):
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]

        reset_memory = config["configurable"].get("reset_memory", False)

        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        history = []
        if reset_memory:
            deleted = clear_namespace_memory(store, namespace)
            print(f"Reset memory for {namespace}; deleted {deleted} items")
            state["memory_reset"] = True
            state["memory_reset_deleted"] = deleted
        else:
            # fetch recent memory
            past = store.search(namespace, query="", limit=2)  # Reduced from 5 to 2 to save tokens
            history = [item.value["message"] for item in past if "message" in item.value]

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break
        return {"messages": history + messages}
    
    def post_model_hook(self, state: AgentState,config: RunnableConfig, *, store: BaseStore):
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
        model="openai/gpt-oss-120b",
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
        middleware=[MemoryMiddleware()],
        system_prompt="""You are a helpful FAQ assistant with memory.
    
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
    reset_memory = bool(payload.get("reset_memory", False))

    config = {
        "configurable": {
            "thread_id": thread_id,
            "actor_id": actor_id,
            "reset_memory": reset_memory
        }
    }

    agent = get_agent()

    result = agent.invoke(
        {"messages": [("human", query)]},
        config=config
    )

    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "No response"
    memory_reset = bool(result.get("memory_reset", False))
    memory_reset_deleted = int(result.get("memory_reset_deleted", 0))

    response = {
        "result": answer,
        "actor_id": actor_id,
        "thread_id": thread_id
    }

    if memory_reset:
        response["memory_reset"] = True
        response["memory_reset_deleted"] = memory_reset_deleted

    return response

print("Launching AgentCore runtime...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentCore runtime and memory utilities")
    parser.add_argument("--reset-memory", action="store_true", help="Reset memory for actor/thread")
    parser.add_argument("--actor-id", default="default-user", help="Actor ID namespace")
    parser.add_argument("--thread-id", default="default-session", help="Thread ID namespace")
    args = parser.parse_args()

    if args.reset_memory:
        store = AgentCoreMemoryStore(memory_id=MEMORY_ID)
        namespace = (args.actor_id, args.thread_id)
        deleted = clear_namespace_memory(store, namespace)
        print(f"Reset memory for {namespace}; deleted {deleted} items")
    else:
        app.run()