"""Streamlit chat interface with message display and multi-modal input."""

import base64
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import httpx
import streamlit as st

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Simple in-memory chat history for basic frontend (will persist later)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_image_base64" not in st.session_state:
    st.session_state.pending_image_base64 = None

# Header
st.title("AI Assistant")
st.caption("Chat with your AI assistant. You can type, add images, files, links, or voice.")

# Voice: upload audio file for Whisper transcription (Web Speech API in browser can be used via external tools)
with st.expander("Voice input (upload audio)"):
    voice_file = st.file_uploader("Upload audio to transcribe", type=["wav", "mp3", "m4a", "webm"], key="voice")
    if voice_file:
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    f"{BACKEND_URL}/transcribe",
                    files={"file": (voice_file.name, voice_file.read())},
                )
            r.raise_for_status()
            text = r.json().get("text", "")
            if text:
                st.session_state.setdefault("transcribed_text", text)
                st.text_area("Transcribed text (edit if needed)", value=text, key="transcribed_edit", height=80)
        except Exception as e:
            st.error(f"Transcription failed: {e}")

# Attach menu (ChatGPT-like + button). Allows adding files, Drive links, or a placeholder for image generation.
if "show_attach_menu" not in st.session_state:
    st.session_state.show_attach_menu = False

col1, col2 = st.columns([0.06, 0.94])
with col1:
    if st.button("+", key="attach_toggle"):
        st.session_state.show_attach_menu = not st.session_state.show_attach_menu
with col2:
    st.markdown("\n")

if st.session_state.show_attach_menu:
    with st.container():
        st.markdown("**Add (choose an option):**")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("Add photos & files", key="attach_files"):
                st.session_state._attach_action = "files"
        with c2:
            if st.button("Add from Google Drive", key="attach_drive"):
                st.session_state._attach_action = "drive"
        with c3:
            if st.button("Create image", key="attach_create"):
                st.session_state._attach_action = "create"

        action = st.session_state.get("_attach_action")
        if action == "files":
            uploaded = st.file_uploader(
                "Add image or document (PNG/JPG/PDF/TXT/MD/DOCX)",
                type=["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "docx"],
                accept_multiple_files=False,
                key="attach_file_uploader",
            )
            if uploaded:
                name = uploaded.name.lower()
                if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    st.session_state.pending_image_base64 = base64.b64encode(uploaded.read()).decode()
                    st.image(base64.b64decode(st.session_state.pending_image_base64), caption=f"Image: {uploaded.name}", use_container_width=True)
                elif name.endswith((".pdf", ".txt", ".md", ".docx")):
                    try:
                        with httpx.Client(timeout=30.0) as client:
                            r = client.post(
                                f"{BACKEND_URL}/ingest",
                                files={"file": (uploaded.name, uploaded.read())},
                            )
                        r.raise_for_status()
                        data = r.json()
                        if data.get("success"):
                            st.success(f"Document '{uploaded.name}' has been learned ({data.get('chunks', 0)} chunks). You can ask questions about it.")
                        else:
                            st.error(data.get("error", "Ingest failed"))
                    except Exception as e:
                        st.error(f"Upload failed: {e}")
                    # Clear action after processing
                    st.session_state._attach_action = None
        elif action == "drive":
            drive_url = st.text_input("Paste Google Drive share link or file URL:", key="drive_url_input")
            if drive_url:
                st.session_state.messages.append({"role": "user", "content": f"[Drive link] {drive_url}", "image_base64": None})
                st.success("Drive link added to the conversation. (Automatic Drive fetch is not implemented yet.)")
                st.session_state._attach_action = None
        elif action == "create":
            prompt_img = st.text_input("Image prompt (placeholder for future generator):", key="create_prompt")
            if st.button("Generate image (placeholder)", key="create_go"):
                st.info("Image generation is not implemented in this demo. Use 'Add photos & files' to upload an image.")
                st.session_state._attach_action = None
else:
    # ensure action cleared when menu hidden
    st.session_state._attach_action = None

# Display message history (text and optional image)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_base64"):
            st.image(
                base64.b64decode(msg["image_base64"]),
                caption="Attached image",
                use_container_width=True,
            )
        st.markdown(msg["content"])

# Chat input: allow pasting transcribed voice text
prompt = st.chat_input("Type your message or paste a link...")
if "transcribed_text" in st.session_state and st.session_state.transcribed_text:
    # Prefill not straightforward in Streamlit chat_input; user can paste from expander
    pass
if prompt:
    image_b64 = st.session_state.pending_image_base64
    st.session_state.pending_image_base64 = None
    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
        "image_base64": image_b64,
    })
    with st.chat_message("user"):
        if image_b64:
            st.image(base64.b64decode(image_b64), caption="Attached", use_container_width=True)
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            payload = {"message": prompt, "history": history}
            if image_b64:
                payload["image_base64"] = image_b64
            with httpx.Client(timeout=60.0) as client:
                r = client.post(f"{BACKEND_URL}/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            response = data.get("response", "")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
            except Exception:
                detail = str(e)
            response = f"Assistant error ({e.response.status_code}): {detail}"
        except Exception as e:
            response = f"Error calling assistant: {e}"
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
