# SEC RAG TOOL (10-K)

## Overview

This tool is a lightweight prototype designed to help financial analysts quickly sift through massive SEC 10-K filings. Instead of manually reading thousands of pages, analysts can query specific companies (e.g., Apple, Tesla, Nvidia) to extract key financial metrics, risk factors, and strategic insights instantly.

The project leverages **Retrieval-Augmented Generation (RAG)** to provide accurate, context-aware answers grounded in official SEC data, complete with source citations.

## Key Features

-   **Multi-Company Support**: Filter queries by company (e.g., AAPL, TSLA, GOOGL, NVDA).
-   **Source Citations**: Every answer includes references to the specific page and section of the 10-K filing.
-   **Automated Ingestion**: A robust ETL pipeline downloads, parses, chunks, and indexes filings automatically.
-   **Containerized Architecture**: Fully Dockerized (Backend, Frontend, Ingestion) for "write once, run anywhere" deployment.
-   **Query Logging**: Built-in functionality to download chat logs for evaluating prototype performance.

## Tech Stack

-   **LLM & Embeddings**: Google Gemini (`gemini-2.0-flash`, `text-embedding-004`)
-   **Vector Database**: Pinecone (Serverless)
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
    *   Retrieves relevant chunks based on user query and selected company filter.
    *   Generates answers using Gemini-2.0-Flash with a strict financial analyst persona.
3.  **User Interface**:
    *   Simple chat interface for interaction and configuration.

## Getting Started

### Prerequisites

*   Docker & Docker Compose
*   API Keys:
    *   **Google AI Studio** (for Gemini)
    *   **Pinecone** (for Vector DB)

### 1. Configuration

Clone the repository and create your environment file:

```bash
git clone git@github.com:raul-muresan03/sec-rag-tool.git
cp .env.example .env
```

Open `.env` and populate your keys:
```ini
GOOGLE_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=sec-rag-index  # Default
SEC_API_EMAIL=your_email@example.com
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

## Future Improvements

*   **Cost Analysis Dashboard**: Integrate token tracking to estimate runtime costs per query.
*   **Expanded Metadata**: Add year-over-year comparison features.
*   **Feedback Loop**: Allow users to rate answers to improve retrieval quality.
*   **Dynamic Ingestion**: Add a UI feature to download and index new companies on the fly.
*   **Comparison Mode**: Compare metrics between two different companies in a single answer.
*   **Citations v2**: Highlight the exact text segment in the source PDF.
*   **Chat History**: Save relevant conversations for access when needed
*   **Financial Charting**: Auto-generate trend lines from extracted data.