import os

from dotenv import load_dotenv

from utils import tools

from langchain_groq import ChatGroq
from langchain.agents import create_agent

load_dotenv()

# LLM

model = ChatGroq(
    model=os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b"),
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