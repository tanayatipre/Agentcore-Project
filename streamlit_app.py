import streamlit as st
import requests
import uuid

# Set up the page with a dark theme and custom title
st.set_page_config(page_title="FAQ Agent", page_icon="🔵", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS for a Persian blue aesthetic
st.markdown("""
<style>

    /* =========================
       MAIN BACKGROUND
    ========================== */

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(88, 130, 255, 0.16), transparent 28%),
            radial-gradient(circle at top right, rgba(120, 90, 255, 0.12), transparent 24%),
            radial-gradient(circle at bottom left, rgba(0, 180, 255, 0.08), transparent 22%),
            linear-gradient(
                145deg,
                #02050d 0%,
                #06152b 42%,
                #020814 100%
            );

        color: #eef4ff;
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

        padding: 68px 58px;

        border-radius: 30px;

        background:
            linear-gradient(
                145deg,
                rgba(8, 18, 38, 0.96),
                rgba(5, 10, 24, 0.94)
            );

        border: 1px solid rgba(120, 170, 255, 0.14);

        box-shadow:
            0 20px 60px rgba(0,0,0,0.65),
            inset 0 1px 0 rgba(255,255,255,0.03);

        backdrop-filter: blur(18px);
    }

    .main-title {
        font-size: clamp(2.4rem, 3vw + 1rem, 5rem);

        font-weight: 800;

        margin: 0;

        color: #edf3ff;

        line-height: 1.12;

        letter-spacing: -1px;

        white-space: normal;
        word-break: break-word;
    }

    .main-title span {
        color: #9bbcff;
        font-weight: 700;
    }

    .subtitle {
        margin-top: 1.4rem;

        text-align: center;

        color: #aab7cf;

        font-size: 1.08rem;

        line-height: 1.7;
    }

    /* =========================
       SESSION TITLE
    ========================== */

    .session-title {
        position: fixed;

        top: 18px;
        left: 18px;

        padding: 10px 14px;

        border-radius: 14px;

        background: rgba(8, 16, 30, 0.82);

        border: 1px solid rgba(140, 180, 255, 0.12);

        color: #dbe8ff;

        font-size: 0.92rem;

        box-shadow: 0 8px 22px rgba(0,0,0,0.4);

        z-index: 9999;
    }

    /* =========================
       CHAT MESSAGE BOXES
       REMOVED DARK SOLID BOXES
    ========================== */

    div[data-testid="stChatMessage"] {
        background: transparent !important;

        border: none !important;

        box-shadow: none !important;

        padding: 0.2rem 0.4rem !important;

        margin-bottom: 1rem !important;
    }

    div[data-testid="stChatMessage"] * {
        color: #f4f7ff;
    }

    /* =========================
       AVATAR / EMOJI COLORS
       PASTEL COOL TONES
    ========================== */

    div[data-testid="stChatMessageAvatarUser"] {
        background:
            linear-gradient(
                145deg,
                #7ecbff,
                #9ab8ff
            ) !important;

        border-radius: 16px !important;
    }

    div[data-testid="stChatMessageAvatarAssistant"] {
        background:
            linear-gradient(
                145deg,
                #b89cff,
                #8fd3ff
            ) !important;

        border-radius: 16px !important;
    }

    /* =========================
       SIDEBAR
    ========================== */

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #081120,
                #030711
            );
    }

    /* =========================
       CHAT INPUT
    ========================== */

    .stChatInputContainer {
        background: transparent !important;

        border: none !important;

        box-shadow: none !important;

        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
    }

    div[data-testid="stChatInput"] {
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }

    div[data-testid="stChatInput"] > div {
        width: 100% !important;

        display: flex !important;

        align-items: center !important;

        flex-direction: row !important;

        flex-wrap: nowrap !important;

        gap: 12px !important;

        background: transparent !important;

        border: none !important;

        box-shadow: none !important;
    }

    div[data-testid="stChatInput"] form {
        display: flex !important;
        align-items: center !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 12px !important;
        width: 100% !important;
        min-width: 0 !important;
    }

    div[data-testid="stChatInput"] textarea {
        width: auto !important;

        flex: 1 1 0 !important;

        min-width: 0 !important;

        min-height: 56px !important;

        resize: none !important;

        background: rgba(255, 255, 255, 0.16) !important;

        color: #f5f8ff !important;

        border-radius: 18px !important;

        border: 1px solid rgba(130, 170, 255, 0.16) !important;

        padding-top: 14px !important;

        box-shadow:
            0 8px 20px rgba(0,0,0,0.25) !important;
    }

    div[data-testid="stChatInput"] button {
        height: 52px !important;

        width: 52px !important;

        border-radius: 14px !important;

        background:
            linear-gradient(
                145deg,
                #88b6ff,
                #7bd7ff
            ) !important;

        border: none !important;

        box-shadow:
            0 8px 18px rgba(0,0,0,0.25) !important;
        flex: 0 0 auto !important;
        margin-left: 6px !important;
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

# Initialize session identifiers and chat history
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

# Display chat messages from history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# React to user input
if prompt := st.chat_input("E.g., Can I use Jio sim?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.session_title:
        words = prompt.strip().split()
        title = " ".join(words[:6])
        st.session_state.session_title = title[:42]

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
                answer = f" **Error {response.status_code}:** Could not get response from the server.\\n\\n{response.text}"
                
        except requests.exceptions.ConnectionError:
            answer = " **Connection Error:** Could not connect to the agent. Make sure `python agentcore_memory.py` is running in another terminal!"
        except Exception as e:
            answer = f" **An error occurred:** {str(e)}"

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(answer)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})
