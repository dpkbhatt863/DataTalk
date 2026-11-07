import re
import streamlit as st
from pipeline import MODEL, MAX_ROWS, make_llm, build_schema_context, FEW_SHOT, ask_database

st.set_page_config(page_title="DataTalk", layout="wide")
st.title("DataTalk")

SAMPLES = [
    "What is the total revenue across all stores?",
    "Top 3 items by total revenue in Sylhet",
    "How many transactions were paid in cash?",
    "What was the total revenue by division in 2017?",
    "Which hour of the day has the most sales?",
]


@st.cache_resource
def load_context():
    return build_schema_context() + "\n" + FEW_SHOT


@st.cache_resource
def load_llm():
    return make_llm(MODEL)


def set_question(q):
    st.session_state.question = q


def safe_md(text):
    return re.sub(r"(?<!\\)\$", r"\\$", text)


with st.sidebar:
    st.header("Sample questions")
    for i, s in enumerate(SAMPLES):
        st.button(s, key=f"sample_{i}", on_click=set_question, args=(s,), use_container_width=True)
    st.divider()
    st.markdown("### Guardrails")
    st.success("PII columns (`contact_no`, `nid`) are hidden from the model and blocked in queries")
    st.success("Read-only: only SELECT / WITH queries are executed")

question = st.text_input(
    "Ask a question about sales, products, stores, or transactions:",
    key="question",
    placeholder="e.g. What were the top 3 items by total revenue in Sylhet?",
)

if st.button("Run Query", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Generating SQL and running it..."):
            result = ask_database(question.strip(), load_llm(), load_context())

        if not result["success"]:
            st.error(f"Could not answer this: {result['error']}")
            if result["sql"]:
                st.code(result["sql"], language="sql")
        else:
            df = result["df"]
            st.subheader("Answer")
            st.success(safe_md(result["answer"]))

            st.subheader("Generated SQL")
            st.code(result["sql"], language="sql")

            st.subheader("Query Results")
            st.dataframe(df, width='stretch')
            note = f"Returned {len(df)} row(s)."
            if len(df) == MAX_ROWS:
                note += f" Showing the first {MAX_ROWS} only."
            st.caption(note)

            st.download_button("Download results as CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name="query_results.csv", mime="text/csv")

st.divider()
st.caption(f"Built with LangChain, Groq ({MODEL}), SQLite and Streamlit")