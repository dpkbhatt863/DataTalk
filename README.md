# DataTalk

Ask a question in plain English, get the SQL, the result table and a short answer back. It runs over a 1,000,000-row retail star schema in SQLite.

I built it to learn how well an LLM can actually write SQL against a real warehouse, so half of this repo is the app and the other half is a benchmark that tests it.

---

---
## 🎬 Interactive Demo

<img width="1900" height="876" alt="texttoSQLgiF" src="https://github.com/user-attachments/assets/f9a66b7d-002f-4bfa-86d4-ce285b618844" />


## How it works

The app uses `openai/gpt-oss-120b` on Groq with three few-shot examples at temperature 0, which was the best-scoring setup in the benchmark below.

```
Question ──> Prompt (schema + join rules + examples) ──> LLM via Groq
         ──> SQL validator (read-only, no PII) ──> SQLite ──> Table + short answer
```

1. **Prompt.** The prompt contains the table definitions and the join rules for the star schema: one `fact_table` joined to `customer_dim`, `item_dim`, `store_dim`, `time_dim` and `trans_dim`. A few worked examples are added on top.
2. **PII is hidden from the model.** `contact_no` and `nid` are left out of the schema the model sees, and the validator also rejects any query that mentions them.
3. **Validation before execution.** Only `SELECT` and `WITH` queries go through. Anything with `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER` or `TRUNCATE` is blocked, and markdown fences around the SQL are stripped. This is a keyword and regex check, not a full SQL parser, so treat it as a safety net rather than a security boundary.
4. **Answer.** The result is shown as a table, with a one-line natural language summary and a CSV download.

## The data

The warehouse is a standard star schema: one big fact table and five small dimension tables.

| Table | Rows | What it holds |
|---|---|---|
| `fact_table` | 1,000,000 | One row per sale: quantity, unit price, total price, and keys to the dimensions |
| `customer_dim` | 9,191 | Customers (including `contact_no` and `nid`, which the app treats as PII) |
| `item_dim` | 264 | Item name, country of manufacture, supplier, unit |
| `store_dim` | 726 | Stores with their division and district |
| `time_dim` | about 100,000 | One row per timestamp, with year, quarter, month and week |
| `trans_dim` | 39 | Payment type and bank |

The database is built from six CSV files by `db_build.ipynb`. It's a short script and I kept it plain:

1. **Read** each CSV, falling back to latin-1 if the file isn't UTF-8.
2. **Clean the column names:** lowercase, and anything other than letters, digits and underscores becomes `_`.
3. **Check the foreign keys.** Every customer, item, store, time and payment key in `fact_table` must exist in its dimension table. If any row points to a missing key, the build stops and says how many.
4. **Write** each table to SQLite.

It never changes the values inside the tables. The data has quirks, such as country names in mixed case (`poland` is lowercase), payment types in lowercase, and units like `ct` and `ct.` stored as separate values. I left them in on purpose, because real warehouses look like this and the benchmark checks whether the model copes with it.

## The benchmark

This is the evaluation part. **eval.ipynb** is the file with all the test experimentations and results. 

It asks each model a fixed set of questions, runs the SQL it writes, and compares the result with the result of a hand-written correct query.

- **30 queries:** 28 that need SQL (11 easy, 12 medium, 5 hard) and 2 guardrail requests that should be blocked, such as asking for customers' phone numbers or deleting records.
- **Scoring:** a query counts as correct when its result set matches the reference. Row order and column names are ignored, text is compared case-insensitively, numbers can differ by 1%, and extra columns are fine.
- **Guardrail queries** pass if the request is blocked or answered without touching PII or writing data.
- **Fair setup:** temperature 0, the same prompt for every model, and the few-shot examples are not in the test set. The notebook has an assertion that fails if a test question is copied into the examples.

### Models tried

| Model | Provider |
|---|---|
| `openai/gpt-oss-120b` | Groq |
| `qwen/qwen3.8-27b` | Groq |
| `gemini-3.5-flash-lite` | Google AI Studio |

### Accuracy (28 SQL queries)

| Model | Prompting | Runs without error | Accuracy | Easy | Medium | Hard | Guardrails |
|---|---|---|---|---|---|---|---|
| gpt-oss-120b | zero-shot | 96–100% | 85.7–89.3% | 90.9% | 83.3% | 80–100% | 2/2 |
| gpt-oss-120b | few-shot (3 examples) | 100% | **100%** | 100% | 100% | 100% | 2/2 |
| qwen3.8-27b | few-shot | 100% | 92.9% | 100% | 100% | 60% | 2/2 |
| gemini-3.5-flash-lite | few-shot | 100% | 96.4% | 100% | 100% | 80% | 2/2 |

The zero-shot row is a range because I ran the benchmark twice and got different results (more on that below). The few-shot rows were identical both times.

### Latency (average per query)

| Model | Prompting | Model call only | End to end |
|---|---|---|---|
| gpt-oss-120b | zero-shot | 1.56s | 8.91s |
| gpt-oss-120b | few-shot | 1.62s | 7.32s |
| qwen3.8-27b | few-shot | 2.86s | 7.08s |
| gemini-3.5-flash-lite | few-shot | 1.89s | 6.56s |

"End to end" includes validation, running the SQL on the 1M-row database and comparing with the reference, so it contains benchmark overhead. The zero-shot run also went first, so it paid the one-time cost of running the reference queries. The app itself is faster than these numbers. The model call is under 3 seconds for every model.

### What I took from it

- **Examples helped the most.** Three examples moved gpt-oss-120b from roughly 86-89% to 100% on both runs, which is 3 to 4 queries out of 28. Most zero-shot misses looked like data conventions that the schema doesn't tell the model, for example countries are stored in mixed case (`poland` is lowercase) and what counts as one sale.
- **The models are close on easy and medium questions.** Almost all the difference is in the hard tier, which has only 5 queries, so one query is 20 points. That's too little to rank the models.
- **I couldn't test Gemini 3.6 Flash.** Its free-tier daily limit ran out partway through and returned rate-limit errors, so I switched to 3.5 Flash-Lite and left 3.6 out of the results.

## Limitations

- 28 SQL queries on one database is a small test. It shows the method works, not that it will hold on a different schema.
- The hard tier has 5 queries, so those numbers are rough.

## Repository structure

```
DataTalk/
├── db_build.ipynb  
├── app.py                       # Streamlit app
├── pipeline.py                  # Prompt, validation and execution
├── eval.ipynb                   # The 30-query benchmark
├── requirements.txt
├── .env.example
└── README.md
```

## Running it

**1. Clone and install**

```bash
git clone https://github.com/YOUR-USERNAME/DataTalk.git
cd DataTalk
pip install -r requirements.txt
```

**2. Add your keys**

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_key   # only needed to run the Gemini rows of the benchmark
```

Never commit `.env`. It should be in `.gitignore`.

**3. Get the database**

- **Just want to run the app?** Skip this step. The repo includes `db/pipeline_db.sqlite.gz`, and the app unpacks it the first time it starts.
- **Want to rebuild it from the raw data?** Put the six CSV files in a `csvs/` folder and run `db_build.ipynb`.

**4. Start the app**

```bash
streamlit run app.py
```

**5. Run the benchmark (optional)**

Open `eval.ipynb` and run the cells in order. The Gemini model is paced to stay inside the free-tier rate limit, so that part takes a few minutes.

## Stack

Python, LangChain, Groq, Google Gemini, SQLite, SQLAlchemy, pandas, Streamlit
