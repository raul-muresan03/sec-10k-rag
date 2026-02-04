import streamlit as st
import requests
import time

st.set_page_config(
    page_title="SEC RAG TOOL",
    page_icon="",
    layout="centered"
)

API_URL = "http://localhost:8000/ask"
HEALTH_URL = "http://localhost:8000/health"

col1, col2 = st.columns([3, 1])

with col1:
    st.title("SEC RAG TOOL")

with col2:
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

if prompt := st.chat_input("Ex: What were the total sales in 2024?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("Analyzing financial data..."):
            try:
                payload = {"question": prompt}
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
                    
                else:
                    error_msg = f"Server Error ({response.status_code}): {response.text}"
                    message_placeholder.error(error_msg)
            
            except requests.exceptions.ConnectionError:
                message_placeholder.error("Backend is not running. Make sure it's running on port 8000.")
            except Exception as e:
                message_placeholder.error(f"Unexpected error: {str(e)}")