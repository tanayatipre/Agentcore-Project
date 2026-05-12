import streamlit as st
import requests
import uuid

st.set_page_config(page_title="FAQ Agent", page_icon="🔵", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>

    /* =========================
       MAIN BACKGROUND
    ========================== */

    .stApp {
        background: #F0EBE3;
        color: #1A1A1A;
    }

    /* =========================
       HERO / TITLE BOX
    ========================== */

    .hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    .title-box {
        width: 94%;
        max-width: 1180px;
        margin: 2.7rem auto;
        padding: 58px 48px;
        border-radius: 20px;
        background: #FFFFFF;
        border: 1px solid #E0DADA;
        box-shadow: 0 12px 30px rgba(0,0,0,0.04);
    }

    .main-title {
        font-size: clamp(2.4rem, 3vw + 1rem, 4.5rem);
        font-weight: 800;
        margin: 0;
        color: #1A1A1A;
        line-height: 1.15;
        letter-spacing: -1px;
        white-space: normal;
        word-break: break-word;
    }

    .main-title span {
        font-weight: 700;
        color: #1A1A1A;
    }

    .subtitle {
        margin-top: 1.2rem;
        text-align: center;
        color: #555555;
        font-size: 1.1rem;
        line-height: 1.6;
        font-weight: 400;
    }

    /* =========================
       SESSION TITLE (CHIP/BADGE)
    ========================== */

    .session-title {
        position: fixed;
        top: 18px;
        left: 18px;
        padding: 8px 16px;
        border-radius: 20px;
        background: #2A2A2A;
        border: none;
        color: #FFFFFF;
        font-size: 0.9rem;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        z-index: 9999;
    }

    /* =========================
       CHAT MESSAGE BOXES
    ========================== */

    div[data-testid="stChatMessage"] {
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 1.2rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        border: 1px solid #E0DADA !important;
    }

    div[data-testid="stChatMessage"]:nth-child(odd) {
        /* User bubble */
        background: #1E1E1E !important;
        border-color: #1E1E1E !important;
    }

    div[data-testid="stChatMessage"]:nth-child(even) {
        /* Assistant bubble */
        background: #FFFFFF !important;
    }

    /* Specific text colors inside bubbles - avoid overriding avatar contents */
    div[data-testid="stChatMessage"]:nth-child(odd) > div > div > div > div {
        color: #FFFFFF !important;
    }
    div[data-testid="stChatMessage"]:nth-child(even) > div > div > div > div {
        color: #1A1A1A !important;
    }

    /* Avatars - Both have white backgrounds and black icons */
    div[data-testid="stChatMessageAvatarUser"],
    div[data-testid="stChatMessageAvatarAssistant"] {
        background: #FFFFFF !important;
        color: #1A1A1A !important;
        border: 1px solid #E0DADA !important;
    }

    div[data-testid="stChatMessageAvatarUser"] *,
    div[data-testid="stChatMessageAvatarAssistant"] * {
        color: #1A1A1A !important;
        fill: #1A1A1A !important;
    }

    /* =========================
       SIDEBAR
    ========================== */

    section[data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E0DADA;
    }
    
    section[data-testid="stSidebar"] * {
        color: #1A1A1A !important;
    }

    /* =========================
       CHAT INPUT
    ========================== */

    .stChatInputContainer {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    .stChatInput {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 0.8rem;
    }

    div[data-testid="stChatInput"] {
        display: flex;
        flex-direction: row !important;
        align-items: center !important;
        width: 100%;
        background: #FFFFFF !important;
        border: 1px solid #E0DADA !important;
        border-radius: 30px !important;
        padding: 4px 6px !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03) !important;
    }
    
    div[data-testid="stChatInput"] textarea {
        background: #F7F3EF !important;
        color: #1A1A1A !important;
        border-radius: 24px !important;
        border: none !important;
        box-shadow: none !important;
        padding: 14px 20px !important;
        flex: 1 1 auto !important;
        min-height: 48px !important;
    }
    
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #9A9A9A !important;
        opacity: 1 !important;
    }

    div[data-testid="stChatInput"] button,
    div[data-testid="stChatInputSubmitButton"] button {
        background: #1A1A1A !important;
        border-radius: 50% !important;
        border: none !important;
        color: #FFFFFF !important;
        width: 44px !important;
        height: 44px !important;
        max-width: 44px !important;
        min-width: 44px !important;
        flex-shrink: 0 !important;
        align-self: center !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        transition: transform 0.15s ease;
        margin-left: 6px !important;
    }
    
    div[data-testid="stChatInput"] button:hover {
        transform: scale(1.05);
    }
    
    div[data-testid="stChatInput"] button svg {
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* =========================
       TABLES
    ========================== */

    table {
        width: 100%;

        border-collapse: collapse;

        margin-top: 15px;
        margin-bottom: 15px;

        overflow: hidden;

        border-radius: 14px;
    }

    th {
        background-color: #121c2d;

        color: #edf3ff;

        padding: 14px;

        text-align: left;

        border-bottom: 1px solid rgba(110,160,255,0.18);
    }

    td {
        padding: 14px;

        border-bottom: 1px solid rgba(255,255,255,0.05);

        color: #d5deea;

        background: rgba(8,12,22,0.85);
    }

    tr:hover td {
        background-color: rgba(20, 30, 48, 0.95);
    }

</style>
""", unsafe_allow_html=True)

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
