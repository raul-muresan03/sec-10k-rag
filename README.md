# SEC RAG TOOL (10-K)

## Overview

This tool is a lightweight prototype designed to help financial analysts quickly sift through massive SEC 10-K filings. Instead of manually reading thousands of pages, analysts can query specific companies (e.g., Apple, Tesla, Nvidia) to extract key financial metrics, risk factors, and strategic insights instantly.

The project leverages **Retrieval-Augmented Generation (RAG)** to provide accurate, context-aware answers grounded in official SEC data, complete with source citations.

## Key Features

-   **Multi-Company Support**: Filter queries by company (e.g., AAPL, TSLA, GOOGL, NVDA).
-   **Source Citations**: Every answer includes references to the specific page and section of the 10-K filing.
-   **Confidence Score**: Each answer includes a 0–1 confidence score based on retrieval quality, source diversity, coverage, and consistency.
-   **Year-over-Year Comparison**: Toggle YoY mode to compare the same metric across two fiscal years (delta + percentage).
-   **Automated Ingestion**: A robust ETL pipeline downloads, parses, chunks, and indexes filings automatically.
-   **Containerized Architecture**: Fully Dockerized (Backend, Frontend, Ingestion) for "write once, run anywhere" deployment.
-   **Query Logging**: Built-in functionality to download chat logs for evaluating prototype performance.

## Tech Stack

-   **LLM Providers**: Google Gemini (`gemini-3.1-flash`), OpenAI, Anthropic, Ollama — selectable per query
-   **Embeddings**: Ollama (`nomic-embed-text`, 768-dim) — local, zero cost
-   **Vector Database**: Pinecone (Serverless, cosine similarity, HNSW index)
-   **Orchestration**: LangChain
-   **Backend**: FastAPI
-   **Frontend**: Streamlit
-   **Data Processing**: `sec-edgar-downloader`, BeautifulSoup4

## Architecture

1.  **ETL Pipeline**:
    *   **Extract**: Downloads raw 10-K HTML from SEC EDGAR.
    *   **Transform**: Cleans HTML, removes noise, and chunks text into semantic segments.
    *   **Load**: Generates embeddings and upserts them to Pinecone with metadata (`ticker`, `section`, `page`).
2.  **RAG Engine**:
    *   Custom retriever (`PineconeScoreRetriever`) injects Pinecone similarity scores into doc metadata.
    *   Confidence formula: `retrieval_quality * 0.35 + coverage * 0.25 + source_diversity * 0.20 + consistency * 0.20` (cosine scores normalized from [0.55, 0.95] → [0, 1]).
    *   YoY comparison: dual Pinecone retrieval (base year + compare year), merged context, comparison prompt.
3.  **User Interface**:
    *   Simple chat interface for interaction and configuration.

## Getting Started

### Prerequisites

*   Docker & Docker Compose
*   API Keys:
    *   **Google AI Studio** (for Gemini) — optional, only if you use cloud provider
    *   **Pinecone** (for Vector DB)

### 1. Configuration

Clone the repository and create your environment file:

```bash
git clone git@github.com:raul-muresan03/sec-rag-tool.git
cp .env.example .env
```

Open `.env` and populate your keys:
```ini
# At minimum — Pinecone is required:
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=sec-rag-tool

# For cloud LLM providers (optional — Ollama local is default):
GOOGLE_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# SEC EDGAR download:
SEC_API_EMAIL=your_email@example.com

# Embeddings — Ollama runs inside Docker, no config needed
```

### 2. Run with Docker

Start the entire application stack:

```bash
docker compose up --build -d
```

### 3. Ingest Data (First Run Only)

To populate the database with filings, run the ingestion container for your desired companies:

```bash
# Ingest data for Apple
docker compose exec ingestion python main.py AAPL 2025

# Ingest data for Tesla
docker compose exec ingestion python main.py TSLA 2025
```
*Note: This process automatically creates the Pinecone index if it doesn't exist.*

### 4. Access the App

*   **Frontend**: [http://localhost:8501](http://localhost:8501)
*   **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Usage Scenarios

Try asking these questions to evaluate the prototype:
*   *"What are the risk factors for Apple?"*
*   *"Who is the CEO of Tesla?"*
*   *"Compare revenue and profit for NVIDIA."*
*   *(YoY mode)* *"What was the total revenue?"* — compares revenue across two fiscal years with delta and percentage.

## Future Improvements

*   **Cost Analysis Dashboard**: Integrate token tracking to estimate runtime costs per query.
*   **LLM Self-Evaluation**: Ask the LLM to rate its own answer faithfulness (LLM-as-judge) for a more calibrated confidence score.
*   **Cross-Company Comparison**: Compare metrics between two different companies in a single answer.
*   **Feedback Loop**: Allow users to rate answers to improve retrieval quality.
*   **Dynamic Ingestion**: Add a UI feature to download and index new companies from the prompt.
*   **Citations v2**: Highlight the exact text segment in the source PDF.
*   **Chat History**: Save relevant conversations for access when needed
*   **Financial Charting**: Auto-generate trend lines from extracted data.