import streamlit as st
import requests
import uuid

# Set up the page with a dark theme and custom title
st.set_page_config(page_title="Jio FAQ Agent", page_icon="🔴", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS for a sleek dark aesthetic
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f14;
        color: #f0f2f5;
    }
    .hero {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        margin: 1.2rem 0 1.4rem;
    }
    .jio-logo {
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ff6b7a, #e0002a 65%);
        display: grid;
        place-items: center;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
        color: #ffffff;
        text-transform: uppercase;
        box-shadow: 0 10px 20px rgba(224, 0, 42, 0.35);
    }
    .main-title {
        font-size: 2.6rem;
        font-weight: 800;
        margin: 0;
        color: #f6f7fb;
    }
    .subtitle {
        text-align: center;
        color: #a7b0bb;
        margin-bottom: 2rem;
    }
    div[data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 1rem;
        box-shadow: 0 8px 18px rgba(0,0,0,0.25);
    }
    div[data-testid="stChatMessage"] * {
        color: #ffffff;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background: linear-gradient(135deg, #1b2736, #1f2c3d);
        border-left: 4px solid #4dd3ff;
    }
    div[data-testid="stChatMessage"]:nth-child(even) {
        background: linear-gradient(135deg, #2a1820, #2c1c25);
        border-left: 4px solid #ff5c7c;
    }
    /* Style tables nicely */
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    th {
        background-color: #2b313e;
        color: #e6edf3;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid #FF3366;
    }
    td {
        padding: 12px;
        border-bottom: 1px solid #2b313e;
        color: #c9d1d9;
    }
    tr:hover td {
        background-color: #2b313e;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
        <div class="jio-logo">Jio</div>
        <h1 class="main-title">Jio Customer Care Assistant</h1>
    </div>
    <div class="subtitle">Ask any question about your Jio services.</div>
    """,
    unsafe_allow_html=True,
)

# Initialize session identifiers and chat history
if "actor_id" not in st.session_state:
    st.session_state.actor_id = f"ui-user-{uuid.uuid4().hex[:8]}"

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"ui-session-{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Session")
    st.caption(f"actor_id: {st.session_state.actor_id}")
    st.caption(f"thread_id: {st.session_state.thread_id}")
    if st.button("New session"):
        st.session_state.thread_id = f"ui-session-{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []
        st.rerun()

# Display chat messages from history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# React to user input
if prompt := st.chat_input("E.g., Can I use Jio sim from Germany?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Show a spinner while waiting for the agent
    with st.spinner("Agent is retrieving FAQ answers..."):
        try:
            # Call the local AgentCore server
            response = requests.post(
                "http://localhost:8080/invocations",
                json={
                    "prompt": prompt,
                    "actor_id": st.session_state.actor_id,
                    "thread_id": st.session_state.thread_id,
                },
                headers={"Content-Type": "application/json"},
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("result", "No result returned.")
            else:
                answer = f"⚠️ **Error {response.status_code}:** Could not get response from the server.\\n\\n{response.text}"
                
        except requests.exceptions.ConnectionError:
            answer = "⚠️ **Connection Error:** Could not connect to the agent. Make sure `python agentcore_memory.py` is running in another terminal!"
        except Exception as e:
            answer = f"⚠️ **An error occurred:** {str(e)}"

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(answer)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})
