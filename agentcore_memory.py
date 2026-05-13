import os
import uuid
import boto3
import argparse
from functools import lru_cache

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from langgraph.store.base import BaseStore

from utils import tools

# Agentcore
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore
from langchain.agents.middleware import AgentMiddleware, AgentState

from dotenv import load_dotenv
_ = load_dotenv()

app = BedrockAgentCoreApp()

# Config
REGION = os.getenv("AWS_REGION", "us-east-1")
MEMORY_ID = os.getenv("AGENTCORE_MEMORY_ID", "customer_care_agent_memory-369OL1GRbv")

def get_groq_api_key():
    local_key = os.getenv("GROQ_API_KEY")
    if local_key:
        return local_key
    try:
        ssm = boto3.client('ssm', region_name=REGION)
        response = ssm.get_parameter(Name='/agentcore/GROQ_API_KEY', WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Failed to fetch GROQ_API_KEY from SSM: {e}")
        return None

GROQ_API_KEY = get_groq_api_key()



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
        model=os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-120b"),
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

if __name__ == "__main__":
    print("Starting app...")
    print("Launching AgentCore runtime...")
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