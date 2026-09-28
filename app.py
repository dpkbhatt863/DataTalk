import streamlit as st
from pipeline import build_llm_schema_context, get_llm, ask_database

st.set_page_config(
    page_title="Sales Warehouse Text-to-SQL Assistant",
    layout="wide",
)
st.title("DataTalk")

# Settings picked during evaluation: temp 0.0 scored 95% vs 90% at 0.7,
# and few-shot prompting added about 5%.
MODEL = "openai/gpt-oss-120b"
TEMP = 0.0

FEW_SHOT_EXEMPLARS = """
### EXEMPLAR QUERY PATTERNS (Use these conventions):

Example 1:
Question: "How many cash transactions were made?"
SQL:
SELECT COUNT(*) AS cash_transactions
FROM fact_table
JOIN trans_dim ON fact_table.payment_key = trans_dim.payment_key
WHERE UPPER(trans_dim.trans_type) = 'CASH';

Example 2:
Question: "What is the total revenue in Sylhet?"
SQL:
SELECT SUM(fact_table.total_price) AS total_revenue
FROM fact_table
JOIN store_dim ON fact_table.store_key = store_dim.store_key
WHERE UPPER(store_dim.division) = 'SYLHET';

Example 3:
Question: "Top 3 items by revenue overall"
SQL:
SELECT item_dim.item_name, SUM(fact_table.total_price) AS total_revenue
FROM fact_table
JOIN item_dim ON fact_table.item_key = item_dim.item_key
GROUP BY item_dim.item_name
ORDER BY total_revenue DESC
LIMIT 3;
"""


@st.cache_resource
def load_context():
    return build_llm_schema_context() + "\n\n" + FEW_SHOT_EXEMPLARS


context = load_context()

SAMPLES = [
    "What is the total revenue across all stores?",
    "Top 3 items by total revenue in Sylhet",
    "How many transactions were paid in cash?",
    "What was the total revenue by division in 2017?",
    "Average quantity sold per transaction in Khulna",
]

with st.sidebar:
    st.header("Quick Sample Questions")
    for sample in SAMPLES:
        if st.button(sample, use_container_width=True):
            st.session_state["selected_question"] = sample

    st.divider()
    st.markdown("### Data Governance & Guardrails")
    st.success("PII Protection: Active (`contact_no`, `nid` masked)")
    st.success("Execution Safety: Read-Only (SELECT statements only)")

question = st.text_input(
    "Ask a question about sales, products, stores, or transactions:",
    value=st.session_state.get("selected_question", ""),
    placeholder="e.g. What were the top 3 items by total revenue in Sylhet?",
)

if st.button("Run Query", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing schema, generating SQL, and fetching results..."):
            llm = get_llm(model_name=MODEL, temperature=TEMP)
            result = ask_database(
                question=question.strip(),
                llm=llm,
                context_str=context,
            )

        if not result["success"]:
            st.error(f"Execution Error: {result['error']}")
        else:
            st.subheader("Answer")
            st.success(result["answer"])

            st.subheader("Generated SQL")
            st.code(result["sql"], language="sql")

            df = result["df"]
            st.subheader("Query Results")
            st.dataframe(df, use_container_width=True)
            st.caption(f"Returned {len(df)} row(s).")

            st.download_button(
                label="Download Results as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="query_results.csv",
                mime="text/csv",
            )

st.divider()
st.caption("Text-to-SQL engine built with LangChain, Groq (openai/gpt-oss-120b), SQLite and Streamlit")