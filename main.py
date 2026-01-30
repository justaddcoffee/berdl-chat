#!/usr/bin/env python3
"""
BERDL Chat - Natural language interface to the BERDL Data Lakehouse.

A demo app that converts natural language questions into SQL queries,
executes them against BERDL, and explains the results using Claude.

Usage:
    python main.py

Environment variables required:
    KB_AUTH_TOKEN - BERDL authentication token
    ANTHROPIC_API_KEY - Anthropic API key for Claude
"""

import os
import httpx
import anthropic
from dotenv import load_dotenv
from nicegui import ui

load_dotenv()

BERDL_API_URL = "https://hub.berdl.kbase.us/apis/mcp/delta/tables/query"

SCHEMA_CONTEXT = """You are a SQL assistant for the BERDL Data Lakehouse (NMDC microbiome data).

Available database: nmdc_core

Key tables and their columns:

1. trait_features - Predicted microbial traits per sample
   - sample_id (string)
   - 90+ columns like: "functional_group:plastic_degradation", "functional_group:methanogenesis",
     "functional_group:nitrogen_fixation", "functional_group:oil_bioremediation",
     "functional_group:human_pathogens_all", "functional_group:cellulolysis", etc.
   - Values are numeric (0 = absent, >0 = present/abundance)

2. abiotic_features - Environmental measurements per sample
   - sample_id, annotations_ph, annotations_temp_has_numeric_value,
     annotations_depth_has_numeric_value, annotations_tot_org_carb_has_numeric_value, etc.

3. taxonomy_dim - Taxonomy hierarchy (2.6M records)
   - taxid, kingdom, phylum, class, order, family, genus, species

4. study_table - Study metadata (48 studies)
   - study_id, name, ecosystem, ecosystem_type, ecosystem_subtype

5. cog_categories - COG functional categories
   - cog_id, category_code, category_name, description

Rules:
- Always use fully qualified table names: nmdc_core.table_name
- Columns with special characters need quotes: "functional_group:plastic_degradation"
- Keep queries simple and limit results (LIMIT 20 unless user asks for more)
- Return ONLY the SQL query, no explanation, no markdown code blocks
"""


def query_berdl(sql: str) -> dict:
    """Execute SQL query against BERDL and return results."""
    token = os.getenv("KB_AUTH_TOKEN")
    if not token:
        return {"error": "KB_AUTH_TOKEN not set in .env"}

    # Basic SQL injection prevention
    if any(keyword in sql.upper() for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]):
        return {"error": "Only SELECT queries are allowed"}

    try:
        response = httpx.post(
            BERDL_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"query": sql, "limit": 100},
            timeout=30.0,
        )
        data = response.json()

        # Check for API errors
        if data.get("error") or data.get("error_type"):
            return {"error": data.get("message", "Unknown API error")}

        return data
    except httpx.TimeoutException:
        return {"error": "Query timed out after 30 seconds"}
    except Exception as e:
        return {"error": str(e)}


def generate_sql(user_question: str) -> str:
    """Use Claude to generate SQL from natural language question."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "-- Error: ANTHROPIC_API_KEY not set"

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SCHEMA_CONTEXT,
        messages=[
            {"role": "user", "content": f"Write a SQL query to answer: {user_question}"}
        ],
    )

    return message.content[0].text.strip()


def explain_results(question: str, sql: str, results: dict) -> str:
    """Use Claude to explain query results in plain English."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set"

    if "error" in results:
        return f"**Query failed:** {results['error']}"

    client = anthropic.Anthropic(api_key=api_key)

    result_data = results.get("result", [])
    result_summary = str(result_data[:10])  # First 10 rows for context
    total_rows = results.get("pagination", {}).get("total_count", len(result_data))

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": f"""The user asked: "{question}"

I ran this SQL: {sql}

Results ({total_rows} rows total, showing first 10):
{result_summary}

Explain what we found in 2-3 sentences. Be specific about numbers and findings."""
            }
        ],
    )

    return message.content[0].text.strip()


def main():
    """Main application entry point."""

    with ui.column().classes("w-full max-w-3xl mx-auto p-4"):
        ui.label("BERDL Chat").classes("text-2xl font-bold mb-2")
        ui.label("Ask questions about NMDC microbiome data in plain English").classes("text-gray-500 mb-2")

        # Connection status
        with ui.row().classes("items-center gap-2 mb-4"):
            status_dot = ui.icon("circle").classes("text-yellow-500 text-xs")
            status_text = ui.label("Checking connection...").classes("text-sm text-gray-500")

        def check_connection():
            result = query_berdl("SELECT 1 as test")
            if "error" in result:
                status_dot.classes("text-red-500", remove="text-yellow-500 text-green-500")
                status_text.set_text(f"Disconnected: {result['error'][:50]}")
            else:
                status_dot.classes("text-green-500", remove="text-yellow-500 text-red-500")
                status_text.set_text("Connected to BERDL")

        ui.timer(0.1, check_connection, once=True)

        # Chat message container
        chat_container = ui.column().classes("w-full space-y-4 mb-4")

        def add_message(role: str, content: str, sql: str = None):
            """Add a message to the chat."""
            with chat_container:
                with ui.card().classes("w-full"):
                    if role == "user":
                        ui.label(content).classes("font-medium")
                    else:
                        ui.markdown(content)
                        if sql:
                            with ui.expansion("Show SQL", icon="code").classes("w-full mt-2"):
                                ui.code(sql, language="sql")

        def send_message():
            question = input_field.value
            if not question.strip():
                return

            input_field.value = ""
            add_message("user", question)

            # Show loading
            with chat_container:
                loading_card = ui.card().classes("w-full")
                with loading_card:
                    ui.spinner("dots")
                    ui.label("Thinking...").classes("text-gray-500")

            # Generate SQL
            sql = generate_sql(question)

            # Execute query
            results = query_berdl(sql)

            # Explain results
            explanation = explain_results(question, sql, results)

            # Remove loading, add response
            chat_container.remove(loading_card)
            add_message("assistant", explanation, sql)

        def set_and_send(question: str):
            input_field.value = question
            send_message()

        # Example questions
        ui.label("Try these:").classes("text-sm text-gray-500 mt-2")
        with ui.row().classes("flex-wrap gap-2 mb-4"):
            examples = [
                "How many samples have plastic degradation?",
                "What kingdoms are in the taxonomy?",
                "Show samples with methanogenesis",
                "Count studies by ecosystem type",
            ]
            for ex in examples:
                ui.button(ex, on_click=lambda e=ex: set_and_send(e)).props("flat dense").classes("text-xs")

        # Input area
        with ui.row().classes("w-full"):
            input_field = ui.input(placeholder="Ask about microbiome data...").classes("flex-grow")
            input_field.on("keydown.enter", send_message)
            ui.button("Send", on_click=send_message).classes("ml-2")

    ui.run(title="BERDL Chat", port=8081)


if __name__ == "__main__":
    main()
