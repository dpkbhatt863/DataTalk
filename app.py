# =============================================================================
# PRODUCTION APP: Text-to-SQL Analytics Assistant
# =============================================================================

import streamlit as st
import pandas as pd
from pipeline import (
    build_llm_schema_context,
    get_llm,
    ask_database,
)

# -------------------- Page Configuration --------------------
st.set_page_config(
    page_title="Sales Warehouse Text-to-SQL Assistant",
    page_icon="📊",
    layout="wide",
)

st.title("📊 DataTalk ")

# -------------------- Hardcoded Production Configuration --------------------
# Derived from Empirical Evaluation Phase:
#   - Temperature 0.0 (Proved 95% accuracy vs 90% at 0.7)
#   - Few-Shot Prompting Enabled (Proved +5% accuracy boost)
OPTIMAL_MODEL = "openai/gpt-oss-120b"
OPTIMAL_TEMP = 0.0

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

# Load base schema context and append Few-Shot exemplars
@st.cache_resource
def load_production_context():
    base_schema = build_llm_schema_context()
    return base_schema + "\n\n" + FEW_SHOT_EXEMPLARS

production_context = load_production_context()

# -------------------- Sidebar Controls --------------------
with st.sidebar:
    st.header("📌 Quick Sample Questions")
    
    sample_questions = [
        "What is the total revenue across all stores?",
        "Top 3 items by total revenue in Sylhet",
        "How many transactions were paid in cash?",
        "What was the total revenue by division in 2017?",
        "Average quantity sold per transaction in Khulna",
    ]
    
    for sample in sample_questions:
        if st.button(sample, use_container_width=True):
            st.session_state["selected_question"] = sample

    st.divider()
    
    st.markdown("### 🛡️ Data Governance & Guardrails")
    st.success("PII Protection: Active (`contact_no`, `nid` masked)")
    st.success("Execution Safety: Read-Only (SELECT statements only)")

# -------------------- Main Interface --------------------

# Handle question input
user_question = st.text_input(
    "Ask a question about sales, products, stores, or transactions:",
    value=st.session_state.get("selected_question", ""),
    placeholder="e.g. What were the top 3 items by total revenue in Sylhet?",
)

if st.button("🚀 Run Query", type="primary"):
    if not user_question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing schema, generating SQL, and fetching results..."):
            # Initialize LLM with optimal parameters
            llm = get_llm(model_name=OPTIMAL_MODEL, temperature=OPTIMAL_TEMP)
            
            # Execute Pipeline
            result = ask_database(
                question=user_question.strip(),
                llm=llm,
                context_str=production_context
            )
        
        # -------------------- Display Results --------------------
        if not result["success"]:
            st.error(f"❌ Execution Error: {result['error']}")
        else:
            # 1. Natural Language Answer
            st.subheader("💡 Answer")
            st.success(result["answer"])
            
            # 2. Generated SQL Query
            st.subheader("📝 Generated SQL")
            st.code(result["sql"], language="sql")
            
            # 3. Tabular Data Output
            st.subheader("📊 Query Results")
            df_results = result["df"]
            st.dataframe(df_results, use_container_width=True)
            st.caption(f"Returned {len(df_results)} row(s).")
            
            # 4. Download CSV Button
            csv_data = df_results.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name="query_results.csv",
                mime="text/csv"
            )

# -------------------- Footer --------------------
st.divider()
st.caption(
    "Production Text-to-SQL Engine | Built with LangChain, Groq (openai/gpt-oss-120b), SQLite & Streamlit"
)