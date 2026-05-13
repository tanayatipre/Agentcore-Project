import streamlit as st
import requests
import uuid

st.set_page_config(page_title="FAQ Agent", page_icon="🔵", layout="centered", initial_sidebar_state="collapsed")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "actor_id" not in st.session_state:
    st.session_state.actor_id = f"ui-user-{uuid.uuid4().hex[:8]}"

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"ui-session-{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_title" not in st.session_state:
    st.session_state.session_title = ""

if st.session_state.session_title:
    st.markdown(
        f"<div class=\"session-title\">{st.session_state.session_title}</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="title-box">
        <div class="hero">
            <h1 class="main-title">
                FAQ Database Assistant<br>
                <span>(With Memory)</span>
            </h1>
        </div>
        <div class="subtitle">
            Ask questions about your services, plans, and customer support.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Session")
    st.caption(f"actor_id: {st.session_state.actor_id}")
    st.caption(f"thread_id: {st.session_state.thread_id}")
    if st.button("New session"):
        st.session_state.thread_id = f"ui-session-{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    avatar_icon = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.markdown(msg["content"])

if prompt := st.chat_input("E.g., Can I use Jio sim?"):
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.session_title:
        words = prompt.strip().split()
        title = " ".join(words[:6])
        st.session_state.session_title = title[:42]

    with st.spinner("Agent is retrieving FAQ answers..."):
        try:
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
                answer = f" **Error {response.status_code}:** Could not get response from the server.\\n\\n{response.text}"
                
        except requests.exceptions.ConnectionError:
            answer = " **Connection Error:** Could not connect to the agent. Make sure `python agentcore_memory.py` is running in another terminal!"
        except Exception as e:
            answer = f" **An error occurred:** {str(e)}"

    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(answer)
    
    st.session_state.messages.append({"role": "assistant", "content": answer})
