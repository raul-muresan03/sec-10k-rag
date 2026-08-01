import streamlit as st
import requests
import time
from config import settings

def _is_na_answer(text):
    lowered = text.lower()
    return "information not available" in lowered or "comparative data not available" in lowered

def _render_confidence(confidence_score):
    if confidence_score >= 0.65:
        color = "green"
        label = "High"
    elif confidence_score >= 0.35:
        color = "orange"
        label = "Medium"
    else:
        color = "red"
        label = "Low"
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;margin-top:4px'>"
        f"<span style='font-size:0.8rem'>Confidence:</span>"
        f"<progress value='{confidence_score}' max='1' style='height:8px;flex:1;accent-color:{color}'></progress>"
        f"<span style='font-size:0.8rem;color:{color};font-weight:bold'>{confidence_score:.2f} ({label})</span>"
        f"</div>",
        unsafe_allow_html=True
    )

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

BACKEND_BASE_URL = settings.backend_url.rstrip("/")
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
        if "usage" in message and message["usage"]:
            usage = message["usage"]
            st.caption(f"Estimated cost: **${usage['estimated_cost']:.6f}** | Total Tokens: **{usage['total_tokens']}** (Input tokens: {usage['input_tokens']}, Output tokens: {usage['output_tokens']})")

        if not _is_na_answer(message.get("content", "")):
            if "sources" in message and message["sources"]:
                with st.expander("Sources (Click for details)"):
                    for s in message["sources"]:
                        st.markdown(f"- {s}")

            if "confidence_score" in message:
                _render_confidence(message["confidence_score"])

with st.sidebar:
    st.header("Configuration")

    available_tickers = ["AAPL", "TSLA", "GOOGL", "NVDA"]
    try:
        companies_response = requests.get(f"{BACKEND_BASE_URL}/companies", timeout=5)
        if companies_response.status_code == 200:
            available_tickers = companies_response.json()
    except Exception:
        pass

    selected_ticker = st.selectbox("Select Company:", available_tickers)
    st.info(f"Analyzing: **{selected_ticker}**")

    compare_yoy = st.checkbox("Enable YoY Comparison", help="Compare metrics across two fiscal years")
    compare_year = None
    if compare_yoy:
        compare_year = st.text_input("Compare Year (e.g., 2023):", placeholder="2024").strip()

    st.markdown("---")
    st.header("AI Model Selection")

    models_data = {"Cloud": {}, "Local": {"ollama": []}}
    try:
        models_response = requests.get(f"{BACKEND_BASE_URL}/models", timeout=5)
        if models_response.status_code == 200:
            models_data = models_response.json()
    except Exception:
        pass

    ai_source = st.radio("AI Source", ["Cloud", "Local"], horizontal=True)

    selected_provider = "google"
    selected_model = "gemini-3.1-flash"

    if ai_source == "Cloud":
        cloud_providers = list(models_data.get("Cloud", {}).keys())
        active_cloud_providers = [p for p in cloud_providers if models_data["Cloud"][p]]

        if not active_cloud_providers:
            st.warning("No Cloud API keys configured. Check .env file.")
        else:
            selected_provider = st.selectbox("Select Provider", active_cloud_providers, format_func=lambda x: x.capitalize())
            available_models = models_data["Cloud"][selected_provider]
            selected_model = st.selectbox("Select Model", available_models)
    else:
        selected_provider = "ollama"
        local_models = models_data.get("Local", {}).get("ollama", [])
        if not local_models:
            st.warning("Ollama is not installed or no models are downloaded. Please visit [ollama.com](https://ollama.com) to install it, then run `ollama pull model_name`.")
            selected_model = ""
        else:
            selected_model = st.selectbox("Select Local Model", local_models)

    st.markdown("---")
    st.header("Ingest New Data")
    new_ticker = st.text_input("Ticker Symbol (e.g., MSFT):").strip().upper()
    new_year = st.text_input("Fiscal Year (e.g., 2024):").strip()

    if st.button("Start Ingestion", use_container_width=True):
        if not new_ticker or not new_year:
            st.error("Please enter both ticker and year.")
        else:
            with st.spinner(f"Ingesting {new_ticker} for {new_year}..."):
                try:
                    payload = {"ticker": new_ticker, "year": new_year}
                    ingest_url = f"{BACKEND_BASE_URL}/ingest"
                    resp = requests.post(ingest_url, json=payload, timeout=120)
                    if resp.status_code == 200:
                        st.success(f"Successfully ingested {new_ticker}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Ingestion failed: {resp.text}")
                except Exception as e:
                    st.error(f"Error connecting to server: {str(e)}")

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
                    "namespace": selected_ticker,
                    "compare_year": compare_year,
                    "provider": selected_provider,
                    "model_name": selected_model
                }
                response = requests.post(API_URL, json=payload, timeout=60)

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer provided.")
                    sources = data.get("sources", [])
                    usage = data.get("usage")
                    confidence_score = data.get("confidence_score", 0.0)

                    message_placeholder.markdown(answer)

                    if usage:
                        st.caption(f"Estimated cost: **${usage['estimated_cost']:.6f}** | Total Tokens: **{usage['total_tokens']}** (Input Tokens: {usage['input_tokens']}, Output Tokens: {usage['output_tokens']})")

                    if not _is_na_answer(answer):
                        if sources:
                            with st.expander("Sources (Click for details)"):
                                for s in sources:
                                    st.markdown(f"- `{s}`")

                        _render_confidence(confidence_score)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "usage": usage,
                        "confidence_score": confidence_score
                    })

                    st.rerun()

                else:
                    error_msg = f"Server Error ({response.status_code}): {response.text}"
                    message_placeholder.error(error_msg)

            except requests.exceptions.ConnectionError:
                message_placeholder.error("Backend is not running. Make sure it's running on port 8000.")
            except Exception as e:
                message_placeholder.error(f"Unexpected error: {str(e)}")