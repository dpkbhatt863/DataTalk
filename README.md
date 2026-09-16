
# 📊 DataTalk — Production Text-to-SQL Engine & Evaluation Suite

DataTalk is a production-grade Text-to-SQL engine and evaluation pipeline that translates natural language analytical questions into executable, secure SQL queries over a **1,000,000-row Star Schema Data Warehouse**.

Built with **LangChain**, **Groq**, **SQLite**, **SQLAlchemy**, and **Streamlit**, DataTalk features dynamic schema context injection, strict security guardrails, data governance, PII masking, and an automated benchmark evaluation framework.

---

## 🏗️ Architecture & Workflow

```text
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│               Prompt Engine                 │
│                                             │
│ • Star Schema Join Context                  │
│ • PII Column Masking                        │
│ • Few-Shot Exemplar Injection               │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│             Groq Inference API              │
│        Llama-3.3-70B / GPT-OSS-20B          │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│             Security Guardrail              │
│                                             │
│ • Read-Only SQL Validator                   │
│ • Code Block Stripper                       │
│ • Destructive Query Blocking                │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│          SQLite Warehouse Engine            │
│           1,000,000 Fact Records             │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│           Synthesized Natural Answer        │
└─────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 1. Star Schema Context Injection

Automatically injects multi-table JOIN rules connecting the central `fact_table` to five dimension tables:

- `customer_dim`
- `item_dim`
- `store_dim`
- `time_dim`
- `trans_dim`

This helps the LLM generate SQL queries that follow the warehouse schema and relationship rules.

### 2. Data Governance & PII Protection

- Removes sensitive customer fields such as `contact_no` and `nid` from the LLM prompt context.
- Applies execution-level restrictions to prevent PII exfiltration.
- Separates analytical access from sensitive customer information.

### 3. SQL Security Guardrails

- Allows read-only `SELECT` and `WITH` statements.
- Blocks destructive operations such as:
  - `DROP`
  - `DELETE`
  - `UPDATE`
  - `ALTER`
- Strips Markdown code fences from generated SQL.
- Uses AST/regex-based validation logic to inspect generated queries.

### 4. Automated Benchmark Framework

Evaluates LLM performance across **20 analytical queries** using:

- Execution Success Rate
- Result Matching Accuracy
- Average Query Latency
- Temperature Sensitivity
- Zero-shot versus few-shot prompting

### 5. Streamlit Web Application

The interactive dashboard includes:

- Natural-language question input
- Quick-sample question buttons
- Generated SQL inspection
- Tabular result display
- Natural-language answer synthesis
- CSV export

---

## 📊 Benchmark & Evaluation Results

DataTalk was benchmarked across **20 analytical queries**, ranging from simple lookups to complex multi-join aggregations over a 1-million-row database.

| Model / Architecture | Strategy | Execution Success Rate | Result Matching Accuracy | Avg. Latency |
|---|---|---:|---:|---:|
| GPT-OSS-20B | Zero-Shot | **100.0%** | **90.0%** | ~1.2s |
| GPT-OSS-20B | Few-Shot (3 Exemplars) | **100.0%** | **95.0%** | ~1.2s |

### Key Experimental Insights

#### 1. Few-Shot In-Context Learning (+5 Percentage Points)

Adding three exemplar queries improved result-matching accuracy from **90.0% to 95.0%**.

The exemplars helped resolve semantic ambiguity around business definitions, such as mapping sales transaction counts to `COUNT(*)`.

#### 2. Deterministic Decoding (Temperature = 0.0)

A temperature of `0.0` performed better than `0.7` in the reported structural SQL correctness tests, suggesting that deterministic decoding may be useful for repeatable SQL-generation tasks.

#### 3. Execution Reliability (100% Reported Execution Rate)

The benchmark reported a 100% execution success rate across the 20-query test set after applying SQL sanitization and validation logic.

> **Note:** These results are specific to the reported benchmark configuration and dataset. They should not be interpreted as a guarantee of performance on unseen schemas, databases, or business questions.

---

## 📁 Repository Structure

```text
DataTalk/
├── app.py                       # Streamlit application dashboard
├── pipeline.py                  # Text-to-SQL engine, validation, and execution
├── text_to_sql_pipeline.ipynb   # R&D notebook, ingestion, experiments, and benchmarks
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
└── README.md                     # Project documentation
```

---

## ⚡ Quickstart

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/DataTalk.git
cd DataTalk
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the API Key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

> Never commit your real API key to version control. Add `.env` to `.gitignore`.

### 4. Launch the Web Application

```bash
streamlit run app.py
```

The Streamlit dashboard will open in your browser.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM Orchestration | LangChain |
| LLM Inference | Groq Cloud API |
| Language Models | Llama-3.3-70B / GPT-OSS-20B |
| Database | SQLite |
| Query Layer | SQLAlchemy |
| Data Engineering | Pandas |
| Tabular Formatting | Tabulate |
| Frontend | Streamlit |
| Evaluation | Custom Benchmark Pipeline |

---

## 👤 Author

**Deepak Bhatt**

---
