import re
import pandas as pd
import os, gzip, shutil
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

DB_PATH = "db/pipeline_db.sqlite"
MODEL = "openai/gpt-oss-120b"
PII_COLUMNS = {"contact_no", "nid"}
MAX_ROWS = 1000

def ensure_db():
    if os.path.exists(DB_PATH):
        return
    if not os.path.exists(DB_PATH + ".gz"):
        raise RuntimeError(f"Database not found: {DB_PATH} or {DB_PATH}.gz")
    with gzip.open(DB_PATH + ".gz", "rb") as f_in, open(DB_PATH + ".tmp", "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    os.replace(DB_PATH + ".tmp", DB_PATH)

ensure_db()
engine = create_engine(f"sqlite:///file:{DB_PATH}?mode=ro&uri=true")

def make_llm(model=MODEL):
    return ChatGroq(model_name=model, temperature=0.0, max_tokens=1024)


def build_schema_context():
    insp = inspect(engine)
    ddl = []
    for t in insp.get_table_names():
        cols = [c["name"] + " " + str(c["type"]) for c in insp.get_columns(t) if c["name"] not in PII_COLUMNS]
        ddl.append("CREATE TABLE " + t + " (" + ", ".join(cols) + ");")
    rules = """STAR SCHEMA JOIN RULES:
- Center table: fact_table
- fact_table.customer_key = customer_dim.customer_key
- fact_table.item_key     = item_dim.item_key
- fact_table.store_key    = store_dim.store_key
- fact_table.time_key     = time_dim.time_key
- fact_table.payment_key  = trans_dim.payment_key
- Always join dimensions through fact_table. Never join two dimensions directly."""
    return "\n".join(ddl) + "\n" + rules


FEW_SHOT = """
### EXAMPLES:
Q: How many sales were paid by mobile payment?
SQL: SELECT COUNT(*) AS mobile_sales FROM fact_table JOIN trans_dim ON fact_table.payment_key = trans_dim.payment_key WHERE UPPER(trans_dim.trans_type) = 'MOBILE';

Q: What was the total revenue in Chittagong in 2016?
SQL: SELECT SUM(fact_table.total_price) AS total_revenue FROM fact_table JOIN store_dim ON fact_table.store_key = store_dim.store_key JOIN time_dim ON fact_table.time_key = time_dim.time_key WHERE UPPER(store_dim.division) = 'CHITTAGONG' AND time_dim.year = 2016;

Q: Which 2 suppliers have the most items?
SQL: SELECT supplier, COUNT(*) AS item_count FROM item_dim GROUP BY supplier ORDER BY item_count DESC LIMIT 2;
"""

SYSTEM = """You are an expert SQL engineer. Generate a valid SQLite query.

{context}

RULES:
1. Return ONLY raw SQL. No markdown fences, no explanations.
2. Write ONLY SELECT statements.
3. Handle case with UPPER() (e.g. UPPER(store_dim.division) = 'SYLHET').
4. Do NOT select PII fields (contact_no, nid)."""
prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "Question: {question}")])

answer_prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer the question in one or two plain sentences, using only the result table provided."),
    ("human", "Question: {question}\n\nResult (first rows):\n{table}"),
])


def generate_sql(question, llm, context):
    return (prompt | llm | StrOutputParser()).invoke({"question": question, "context": context}).strip()


def validate_sql(raw):
    sql = re.sub(r"^```(?:sql)?\s*", "", raw.strip(), flags=re.I)
    sql = re.sub(r"\s*```$", "", sql).rstrip(";").strip()
    up = sql.upper()
    if not up.startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are permitted.")
    for w in ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]:
        if re.search(rf"\b{w}\b", up):
            raise ValueError(f"Forbidden keyword: {w}")
    for pii in ["CONTACT_NO", "NID"]:
        if re.search(rf"\b{pii}\b", up):
            raise ValueError(f"PII field blocked: {pii}")
    return sql


def run_sql(sql, max_rows=None):
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchmany(max_rows) if max_rows else result.fetchall()
        return pd.DataFrame(rows, columns=list(result.keys()))


def summarize(question, df, llm):
    if df.empty:
        return "The query ran but returned no rows."
    try:
        table = df.head(20).to_string(index=False)
        return (answer_prompt | llm | StrOutputParser()).invoke({"question": question, "table": table}).strip()
    except Exception:
        return f"Returned {len(df)} row(s)."


def ask_database(question, llm, context):
    sql = None
    try:
        sql = validate_sql(generate_sql(question, llm, context))
        df = run_sql(sql, max_rows=MAX_ROWS)
    except Exception as e:
        return {"success": False, "error": str(e), "sql": sql}
    return {"success": True, "sql": sql, "df": df, "answer": summarize(question, df, llm)}