# AskSheets — AI-Powered Spreadsheet Assistant

Chat with your spreadsheets and PDFs in plain English. Upload a CSV, Excel, or PDF — then ask anything about your data. AskSheets generates SQL under the hood, queries your data with DuckDB, and explains the answer conversationally. No spreadsheet skills required.

---

## What it does

- **Upload & analyze** — supports CSV, Excel (.xlsx/.xls), and PDFs with tables
- **Natural language queries** — ask things like *"which region had the highest sales last month?"* and get a real answer with the data behind it
- **General AI chat** — when no file is loaded, it works as a regular conversational assistant
- **Secure accounts** — JWT-based login with bcrypt password hashing

## How it works

```
You ask a question
    → LLM generates a DuckDB SQL query against your data
    → Query runs on the uploaded DataFrame
    → LLM narrates the result in plain English
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| LLM | OpenRouter — minimax/minimax-m2.5 |
| Query engine | DuckDB |
| File parsing | pandas, pdfplumber, openpyxl |
| Auth | JWT + bcrypt |
| User database | SQLite |
| Frontend | Vanilla JS, HTML5, CSS3 |

---

## Local setup

### Prerequisites

- Python 3.10 or higher
- An [OpenRouter](https://openrouter.ai) API key (free tier available — no credit card required)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/asksheets.git
cd asksheets

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and paste in your OpenRouter API key

# 5. Start the server
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000), create an account, upload a file, and start asking questions.

---

## Environment variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | Your OpenRouter API key |
| `ASKSHEETS_SECRET_KEY` | No | JWT signing secret. Set a long random string in production. |
| `REQUIRE_AUTH` | No | Set to `true` to enforce login on all data routes. Defaults to `false`. |

---


## Project structure

```
asksheets/
├── app/
│   ├── main.py              # FastAPI app and all routes
│   ├── cache/               # Uploaded DataFrames stored as pickles
│   ├── services/
│   │   ├── auth_db.py       # SQLAlchemy User model and DB init
│   │   ├── auth_utils.py    # JWT creation, bcrypt hashing, dependencies
│   │   ├── ingest.py        # CSV / Excel / PDF → pandas DataFrame
│   │   ├── jsonsafe.py      # Converts NumPy/pandas types to JSON-safe values
│   │   ├── nlg.py           # LLM result narration (answer generation)
│   │   ├── sqlexec.py       # Runs SQL against DataFrames via DuckDB
│   │   └── sqlgen.py        # NL question → DuckDB SQL via LLM
│   └── static/
│       ├── app.js           # Chat UI logic
│       ├── chat.html
│       ├── login.html
│       ├── signup.html
│       └── styles.css
├── .env.example
├── .gitignore
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

---

## Limitations

- Uploaded files are cached in `app/cache/` as pickle files. These are session-scoped and will disappear on server restart (by design for a stateless portfolio deploy).
- PDF analysis only works on PDFs with real tables — scanned/image PDFs are not supported.
- The app uses minimax/minimax-m2.5 via OpenRouter. You can swap in any OpenRouter-compatible model by changing the `model` field in `app/main.py`.

---

## License

MIT © 2025 Abhishek SS