from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

import os
import uuid
import pickle
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .services.ingest import read_any
from .services.jsonsafe import make_json_safe
from .services.sqlgen import make_sql, rewrite_sql_bad
from .services.sqlexec import run_sql_with_retry
from .services.nlg import narrate
from .services.auth_db import init_db, User
from .services.auth_utils import (
    get_db,
    hash_password,
    authenticate_user,
    create_access_token,
    get_current_user,
)

# Set to "true" in your .env to require a valid JWT on upload/ask routes
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

CHAT_SYSTEM = (
    "You are AskSheets, a friendly and knowledgeable assistant. "
    "Answer questions directly and conversationally on any topic — "
    "data analysis, general knowledge, advice, or just a chat. "
    "If a dataset is uploaded you can also analyze it; mention this if relevant. "
    "Keep responses clear and concise, typically 2–4 sentences."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AskSheets", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(ds_id: str) -> Path:
    return CACHE / f"{ds_id}.pkl"


def save_df(ds_id: str, df) -> None:
    with _cache_path(ds_id).open("wb") as f:
        pickle.dump(df, f)


def load_df(ds_id: str):
    p = _cache_path(ds_id)
    if not p.exists():
        return None
    with p.open("rb") as f:
        return pickle.load(f)


def _build_llm(temperature: float = 0.7) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key is not configured")
    return ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model="minimax/minimax-m2.5",
        temperature=temperature,
    )


def _maybe_require_user(token_user=Depends(get_current_user)):
    return token_user if REQUIRE_AUTH else None


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return FileResponse("app/static/login.html")


@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")


@app.get("/signup")
def signup_page():
    return FileResponse("app/static/signup.html")


@app.get("/chat")
def chat_page():
    return FileResponse("app/static/chat.html")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    exists = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username or email is already taken")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    return {"msg": "Account created — please log in"}


@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# ── Data routes ───────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    _user=Depends(_maybe_require_user),
):
    """Parse a CSV, Excel, or PDF file and store the DataFrame for later queries."""
    content = await file.read()
    df, kind = read_any(content, file.filename)

    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="No tabular data found in the uploaded file")

    ds_id = uuid.uuid4().hex[:12]
    save_df(ds_id, df)

    return {
        "dataset_id": ds_id,
        "type": kind,
        "columns": df.columns.tolist(),
        "rows": len(df),
    }


@app.post("/ask")
async def ask(
    payload: dict,
    _user=Depends(_maybe_require_user),
):
    """
    Answer a question. If a dataset_id is supplied, query the uploaded data.
    Otherwise, fall back to general conversational chat.
    """
    ds_id = payload.get("dataset_id")
    question = (payload.get("query") or "").strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    llm = _build_llm()

    # No dataset uploaded — general chat mode
    if not ds_id:
        response = llm.invoke([
            SystemMessage(content=CHAT_SYSTEM),
            HumanMessage(content=question),
        ])
        return JSONResponse({"answer": response.content})

    # Dataset mode — NL → SQL → DuckDB → narrated answer
    df = load_df(ds_id)
    if df is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found. Please re-upload your file.",
        )

    sql = make_sql(question, df)

    result_df, final_sql = run_sql_with_retry(
        df, sql, lambda s, e: rewrite_sql_bad(s, e, df)
    )

    # If the LLM flagged the question as small-talk, fall back to general chat
    if "smalltalk" in result_df.columns:
        response = llm.invoke([
            SystemMessage(content=CHAT_SYSTEM),
            HumanMessage(content=question),
        ])
        return JSONResponse({"answer": response.content})

    rows = result_df.to_dict(orient="records")

    if result_df.shape == (1, 1):
        val = list(rows[0].values())[0]
        answer = narrate(question, final_sql, {"value": val})
    else:
        answer = narrate(question, final_sql, rows[:50])

    return JSONResponse({
        "answer": answer,
        "rows": make_json_safe(rows[:200]),
        "sql": final_sql,
    })