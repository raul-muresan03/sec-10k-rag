import sqlite3
import os
from typing import Dict, Any
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

DB_PATH = "data/token_usage.db"

GEMINI_PRICING = {
    "flash": {
        "input": 0.075 / 1000000,
        "output": 0.30 / 1000000
    },
    "pro": {
        "input": 1.25 / 1000000,
        "output": 5.00 / 1000000
    }
}


class TokenTrackerCallback(BaseCallbackHandler):
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "message"):
                        msg = gen.message
                        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                            self.input_tokens = msg.usage_metadata.get("input_tokens", 0)
                            self.output_tokens = msg.usage_metadata.get("output_tokens", 0)
                            self.total_tokens = msg.usage_metadata.get("total_tokens", 0)

def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        query TEXT,
        namespace TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        total_tokens INTEGER,
        estimated_cost REAL,
        model_name TEXT
    )
    """)

    conn.commit()
    conn.close()

def log_query_usage(query: str, namespace: str, input_tokens: int, output_tokens: int, model_name: str) -> Dict[str, Any]:
    init_db()

    model_name_lowercase = model_name.lower()
    pricing_tier = "pro" if "pro" in model_name_lowercase else "flash"

    input_rate = GEMINI_PRICING[pricing_tier]["input"]
    output_rate = GEMINI_PRICING[pricing_tier]["output"]

    total_tokens = input_tokens + output_tokens

    cost = (input_tokens * input_rate) + (output_tokens * output_rate)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
    """
    INSERT INTO query_logs (query, namespace, input_tokens, output_tokens, total_tokens, estimated_cost, model_name)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (query, namespace, input_tokens, output_tokens, total_tokens, cost, model_name))

    conn.commit()
    conn.close()

    return {
        "input_tokens" : input_tokens,
        "output_tokens" : output_tokens,
        "total_tokens" : total_tokens,
        "estimated_cost" : cost
    }


def get_aggregated_stats() -> Dict[str, Any]:
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(estimated_cost), 0.0),
            COUNT(*),
            COALESCE(SUM(input_tokens), 0),
            COALESCE(SUM(output_tokens), 0),
            COALESCE(SUM(total_tokens), 0),
            COALESCE(AVG(estimated_cost), 0.0)
        FROM query_logs
        """
    )

    query1 = cursor.fetchone()
    total_cost, total_queries, total_input_tokens, total_output_tokens, total_tokens, average_cost_per_query = query1

    cursor.execute(
        """
        SELECT
            namespace,
            COUNT(*),
            COALESCE(SUM(total_tokens), 0),
            COALESCE(SUM(estimated_cost), 0.0)
        FROM query_logs
        GROUP BY namespace
        """
    )

    query2 = cursor.fetchall()

    conn.close()

    usage_by_namespace = [
        {
            "namespace": i[0],
            "query_count": i[1],
            "total_tokens": i[2],
            "total_cost": i[3]
        }
        for i in query2
    ]

    return {
        "total_cost": total_cost,
        "total_queries": total_queries,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "average_cost_per_query": average_cost_per_query,
        "usage_by_namespace": usage_by_namespace
    }