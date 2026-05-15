# Agentcore FAQ Database Assistant

<img width="753" height="813" alt="Screenshot 2026-05-13 173433" src="https://github.com/user-attachments/assets/aa9cc6e4-5df0-4a48-8bd1-64f43d010e0a" />

This project is a retrieval-augmented FAQ assistant for Jio customer care. It runs a local AgentCore runtime, queries a FAISS index built from a Jio FAQ dataset, and serves answers through an HTTP endpoint and an optional Streamlit UI.

## What I've used

- Python 3.13 runtime (AgentCore runtime)
- AWS Bedrock AgentCore runtime SDK
- LangChain + LangGraph for agent orchestration
- FAISS for local vector search
- Amazon Bedrock embeddings (amazon.titan-embed-text-v2:0)
- Groq-hosted LLM via LangChain (model name configured in code)
- Streamlit for the UI

## Dataset

I'v extracted the FAQ dataset from the official Jio website (https://www.jio.com/) and it is stored in `jio_faq.csv`. The vector index is built from this dataset and stored in `faiss_index/`.

## The Workflow

1. Build the FAISS index from the CSV dataset.
2. Start the AgentCore runtime locally.
3. Send prompts to the runtime via HTTP or through the Streamlit UI.
4. The agent retrieves relevant FAQ entries from FAISS and uses the LLM to respond.

<img width="1025" height="878" alt="Screenshot 2026-05-13 235512" src="https://github.com/user-attachments/assets/2a64aa27-b3a8-488a-a4a3-b8311f085eb6" />

## Runtime flow (API request)

1. Client sends a JSON payload to the local runtime endpoint.
2. The runtime loads the FAISS index and embeds the query using Bedrock embeddings.
3. The agent calls tools to retrieve relevant FAQ content.
4. The LLM generates a response based only on retrieved content.
5. The response is returned to the client.

## APIs and services used

- AWS Bedrock AgentCore runtime API
- AWS Systems Manager Parameter Store (optional, for `GROQ_API_KEY`)
- Amazon Bedrock embeddings API (Titan Text Embeddings v2)
- Groq LLM API via LangChain

## Project structure

- `agentcore_memory.py`: Main AgentCore runtime with tools, memory middleware, and HTTP entrypoint.
- `agentcore_runtime.py`: Alternate runtime entrypoint without memory extensions.
- `langgraph_agent.py`: Local test runner for the agent.
- `build_index.py`: Builds the FAISS index from `jio_faq.csv`.
- `streamlit_app.py`: Streamlit UI for chat.
- `faiss_index/`: Local FAISS index files.

## Setup

1. Install dependencies:

   ```bash
    uv sync
   ```

2. Set environment variables (Get your GROQ API key from [GROQ](https://groq.com/)):

   ```bash
   export GROQ_API_KEY="your_key"
   ```

   Optionally store the key in AWS SSM Parameter Store as `/agentcore/GROQ_API_KEY`.

3. Build the FAISS index:

   ```bash
   python build_index.py
   ```

## Run the AgentCore runtime

```bash
python agentcore_memory.py
```

The runtime listens on `http://localhost:8080/invocations`.

This repository supports two ways to run the runtime:

- Local mode with `python agentcore_memory.py` (fast iteration and debugging)
- Managed mode with `agentcore launch` (builds and runs the runtime in AWS)

The local runtime includes memory support through AgentCore Memory. A memory namespace is created per `actor_id` and `thread_id`.

### Test local runtime (Example request)

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Can I activate Jio eSIM online?","actor_id":"user-1","thread_id":"session-1"}'
```

## Run the Streamlit UI

```bash
streamlit run streamlit_app.py
```

The UI sends prompts to the local runtime and includes per-session `actor_id` and `thread_id` to keep memory scoped to a session.

## AWS requirements

- Access to AWS Bedrock AgentCore runtime in the configured region.
- IAM role permissions for AgentCore runtime and optional SSM access.


## Limitations

- The agent can only answer questions based on the FAQ data provided in the CSV file.
- The agent cannot access any external resources or APIs.

## Future improvements

- Use Vector Search instead of FAISS for better scalability.
- Implement a more sophisticated memory system.
- Add support for more tools.
- Add support for more data sources.



# Troubleshooting common issues

1. **Connection Refused**:
   - Ensure the AgentCore runtime is running.
   - Check that the port (default 8080) is not in use.

2. **Authentication Errors**:
   - Verify that `GROQ_API_KEY` is set correctly.

3. **Bedrock API Errors**:
   - Check AWS credentials and region configuration.
   - Ensure the Bedrock runtime is available in your region.
