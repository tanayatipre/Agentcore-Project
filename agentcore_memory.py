import csv
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

# AgentCore
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph_checkpoint_aws import AgentCoreMemorySaver, AgentCoreMemoryStore
from langchain.agents.middleware import AgentMiddleware, AgentState

from dotenv import load_dotenv

_ = load_dotenv()

app = BedrockAgentCoreApp()

# ==============================
# CONFIG
# ==============================
REGION = "us-east-1"
MEMORY_ID = "customer_care_agent_memory-369OL1GRbv"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==============================
# LOAD DATA (LIGHTWEIGHT)
# ==============================
@lru_cache
def load_faq_csv(path: str = "./lauki_qna.csv") -> List[Document]:
    docs = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row["question"].strip()
            a = row["answer"].strip()
            docs.append(Document(page_content=f"Q: {q}\nA: {a}"))
    return docs


# ==============================
# SIMPLE SEARCH 
# ==============================
def simple_search(query: str, docs: List[Document], k=3):
    query = query.lower()
    scored = []

    for doc in docs:
        text = doc.page_content.lower()
        score = sum(word in text for word in query.split())
        scored.append((score, doc))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [doc for score, doc in scored[:k] if score > 0]


# ==============================
# TOOLS
# ==============================
@tool
def search_faq(query: str) -> str:
    """Search FAQ data for relevant answers."""
    docs = load_faq_csv()
    results = simple_search(query, docs, k=3)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} relevant FAQ entries:\n\n{context}"


@tool
def search_detailed_faq(query: str, num_results: int = 5) -> str:
    """Search FAQ with more results."""
    docs = load_faq_csv()
    results = simple_search(query, docs, k=num_results)

    if not results:
        return "No relevant FAQ entries found."

    context = "\n\n---\n\n".join([
        f"FAQ Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Found {len(results)} detailed FAQ entries:\n\n{context}"


@tool
def reformulate_query(original_query: str, focus_aspect: str) -> str:
    """Reformulate query to focus on a specific aspect."""
    docs = load_faq_csv()
    reformulated = f"{focus_aspect} {original_query}"
    results = simple_search(reformulated, docs, k=3)

    if not results:
        return f"No results found for aspect: {focus_aspect}"

    context = "\n\n---\n\n".join([
        f"Entry {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(results)
    ])

    return f"Results for '{focus_aspect}':\n\n{context}"


tools = [search_faq, search_detailed_faq, reformulate_query]

# ==============================
# MEMORY MIDDLEWARE
# ==============================
class MemoryMiddleware(AgentMiddleware):

    def pre_model_hook(self, state: AgentState, config: RunnableConfig, *, store: BaseStore):
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]

        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break

        return {"messages": messages}

    def post_model_hook(self, state, config: RunnableConfig, *, store: BaseStore):
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]

        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break

        return state


# ==============================
# LLM + AGENT
# ==============================
@lru_cache
def get_llm():
    return init_chat_model(
        model="openai/gpt-oss-20b",
        model_provider="groq",
        api_key=GROQ_API_KEY,
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
Be clear and concise.""",
    )


# ==============================
# ENTRYPOINT
# ==============================
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