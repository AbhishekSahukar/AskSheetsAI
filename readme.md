# 💬 AskSheets — AI Spreadsheet & Chat Assistant

AskSheets lets you **chat with your spreadsheets and PDFs** — or just have a friendly AI conversation.  
Upload a **CSV, Excel, or PDF**, ask questions in plain English, and get **dynamic analysis** powered by LLMs.  

Built with **FastAPI**, **LangChain**, **OpenRouter (Mistral)**, and a clean **Vanilla JS frontend**.

---

## Features

-  **Login & Signup** with JWT authentication (SQLite for persistence)
-  **Upload CSV, Excel, or PDF** files for analysis
-  **Natural language questions** → auto SQL generation → DataFrame query
-  **General chatbot mode** when no file is uploaded
-  Summaries, calculations, and insights over your data
-  Clean chat-style **UI/UX** with bubbles, glossy login cards, and file upload
-  

## 🛠️ Tech Stack

### Backend
- FastAPI — web framework
- LangChain — LLM orchestration
- OpenRouter (Mistral models) — LLM provider
- SQLAlchemy — ORM for user management
- DuckDB — query execution on uploaded data

### Frontend
- Vanilla JavaScript — chat logic and interactivity
- HTML5 — page structure
- CSS3 — styling (dark glossy UI, chat bubbles, auth cards)

### Authentication & Security
- JWT (JSON Web Tokens) — session management
- Passlib (bcrypt) — password hashing

### Database
- SQLite — local storage for users and auth

## ⚡ Getting Started

### 1. Clone the repo

bash
git clone https://github.com/yourusername/asksheets.git
cd asksheets

### 2.Setup Python environment

python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

pip install -r requirements.txt

### 3.Setup environment variables
OPENROUTER_API_KEY=your-openrouter-key

### 4. Run the app
uvicorn app.main:app --reload

### License
MIT License © 2025 Abhishek SS