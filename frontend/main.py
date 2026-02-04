import streamlit as st
import requests
import time
import os

def convert_chat_to_txt():
    log_content = ""
    
    if "messages" in st.session_state:
        for msg in st.session_state.messages:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            log_content += f"[{role}]:\n{msg['content']}\n"
            
            if "sources" in msg and msg["sources"]:
                source_list = ", ".join(msg["sources"])
                log_content += f"[Sources]: {source_list}\n"
            
            log_content += "\n" + "-"*30 + "\n\n"
            
    return log_content

st.set_page_config(
    page_title="SEC RAG TOOL",
    layout="centered"
)

BACKEND_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_URL = f"{BACKEND_BASE_URL}/ask"
HEALTH_URL = f"{BACKEND_BASE_URL}/health"

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.title("SEC RAG TOOL")

with col2:
    st.write("##")
    chat_log = convert_chat_to_txt()
    
    st.download_button(
        label="Download Log",
        data=chat_log,
        file_name="chat_log.txt",
        mime="text/plain",
        use_container_width=True
    )

with col3:
    st.write("##")
    if st.button("System Check", use_container_width=True):
        try:
            response = requests.get(HEALTH_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                st.toast(f"Backend: {data.get('status', 'Online')}")
                st.toast(f"Pinecone: {data.get('checks', {}).get('pinecone', 'Unknown')}")
            else:
                st.error(f"Backend Error: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("Backend Offline")

st.markdown("""
This tool allows you to query and analyze financial data from SEC filings using a conversational interface. Ask questions about financial metrics, trends, and more!
""")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("Sources (Click for details)"):
                for s in message["sources"]:
                    st.markdown(f"- {s}")

with st.sidebar:
    st.header("Configuration")
    company_map = {
        "Apple (AAPL)": "AAPL",
        "Tesla (TSLA)": "TSLA",
        "Google (GOOGL)": "GOOGL",
        "Nvidia (NVDA)": "NVDA"
    }
    selected_option = st.selectbox("Select Company:", list(company_map.keys()))
    selected_ticker = company_map[selected_option]
    
    st.info(f"Analyzing: **{selected_ticker}**")

if prompt := st.chat_input("Ex: What were the total sales in 2024?"):
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner(f"Analyzing financial data for {selected_ticker}..."):
            try:
                payload = {
                    "question": prompt, 
                    "namespace": selected_ticker
                }
                response = requests.post(API_URL, json=payload, timeout=60)
            
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer provided.")
                    sources = data.get("sources", [])
                    
                    message_placeholder.markdown(answer)
                    
                    if sources:
                        with st.expander("Sources (Click for details)"):
                            for s in sources:
                                st.markdown(f"- `{s}`")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })

                    st.rerun()
                    
                else:
                    error_msg = f"Server Error ({response.status_code}): {response.text}"
                    message_placeholder.error(error_msg)
        
            except requests.exceptions.ConnectionError:
                message_placeholder.error("Backend is not running. Make sure it's running on port 8000.")
            except Exception as e:
                message_placeholder.error(f"Unexpected error: {str(e)}")