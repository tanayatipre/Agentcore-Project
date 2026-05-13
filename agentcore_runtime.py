import os
from functools import lru_cache

from utils import tools

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



# LLM

model = ChatGroq(
    model=os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b"),
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