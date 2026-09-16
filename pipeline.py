# pipeline.py
import os
import re
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "db/pipeline_db.sqlite"
PII_COLUMNS = {"contact_no", "nid"}

# ---------- Schema Context ----------
def build_llm_schema_context(db_path: str = DB_PATH) -> str:
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    ddl = []
    for table in inspector.get_table_names():
        cols = [
            f"{c['name']} {c['type']}"
            for c in inspector.get_columns(table)
            if c["name"] not in PII_COLUMNS
        ]
        ddl.append(f"CREATE TABLE {table} ({', '.join(cols)});")
    engine.dispose()

    joins = """
STAR SCHEMA JOIN RULES:
- Center: fact_table
- fact_table.customer_key = customer_dim.customer_key
- fact_table.item_key     = item_dim.item_key
- fact_table.store_key    = store_dim.store_key
- fact_table.time_key     = time_dim.time_key
- fact_table.payment_key  = trans_dim.payment_key
- Always join dimensions through fact_table. Never join two dims directly.
"""
    return "\n".join(ddl) + "\n" + joins.strip()


# ---------- LLM ----------
def get_llm(model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.0):
    return ChatGroq(
        model_name=model_name,
        temperature=temperature,
        api_key=os.getenv("GROQ_API_KEY"),
    )


# ---------- SQL Generation ----------
def generate_sql(question: str, llm, context_str: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert SQLite engineer. Generate a valid SQLite query.

{context_str}

RULES:
1. Return ONLY raw SQL. No markdown, no explanation.
2. ONLY SELECT / WITH statements.
3. Use UPPER() for string filters (e.g. UPPER(division) = 'SYLHET').
4. Never select PII columns (contact_no, nid).
5. Prefer COUNT(*) for transaction counts unless asked for distinct.
"""),
        ("human", "Question: {question}")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"question": question, "context_str": context_str}).strip()


def sanitize_and_validate_sql(raw_sql: str) -> str:
    sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql.strip(), flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql).rstrip(";").strip()
    upper = sql.upper()

    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError("Only SELECT queries are allowed.")

    for word in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]:
        if re.search(rf"\b{word}\b", upper):
            raise ValueError(f"Forbidden keyword: {word}")

    for pii in ["CONTACT_NO", "NID"]:
        if re.search(rf"\b{pii}\b", upper):
            raise ValueError(f"PII column blocked: {pii}")

    return sql


def execute_sql(sql: str, db_path: str = DB_PATH) -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    engine.dispose()
    return df


def synthesize_answer(question: str, sql: str, df: pd.DataFrame, llm) -> str:
    if df.empty:
        return "No records found for your request."
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a concise data analyst. Answer clearly using the results."),
        ("human", "Question: {q}\nSQL: {sql}\nResults:\n{data}\n\nShort answer:")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "q": question,
        "sql": sql,
        "data": df.head(15).to_markdown(index=False)
    })


def ask_database(question: str, llm, context_str: str) -> dict:
    try:
        raw = generate_sql(question, llm, context_str)
        sql = sanitize_and_validate_sql(raw)
        df = execute_sql(sql)
        answer = synthesize_answer(question, sql, df, llm)
        return {"success": True, "sql": sql, "df": df, "answer": answer, "error": None}
    except Exception as e:
        return {"success": False, "sql": None, "df": None, "answer": None, "error": str(e)}