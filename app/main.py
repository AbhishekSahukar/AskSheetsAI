
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
from langchain.schema import SystemMessage, HumanMessage


from .services.ingest import read_any
from .services.jsonsafe import make_json_safe
from .services.sqlgen import make_sql, rewrite_sql_bad
from .services.sqlexec import run_sql_with_retry
from .services.nlg import narrate


from .services.auth_db import init_db, User
from .services.auth_utils import (
    get_db, hash_password, authenticate_user,
    create_access_token, get_current_user
)


REQUIRE_AUTH = False  


app = FastAPI(title="AskSheets")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/")
def home():
    return FileResponse("app/static/login.html")

@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")

@app.get("/signup")
def signup_page():
    return FileResponse("app/static/signup.html")


CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

def _path(ds_id: str) -> Path:
    return CACHE / f"{ds_id}.pkl"

def save_df(ds_id, df) -> None:
    with _path(ds_id).open("wb") as f:
        pickle.dump(df, f)

def load_df(ds_id):
    p = _path(ds_id)
    if not p.exists():
        return None
    with p.open("rb") as f:
        return pickle.load(f)


CHAT_SYS = (
    "You are AskSheets, a friendly, knowledgeable chatbot. "
    "Always answer user questions directly and conversationally, even if they are about general topics "
    "like cars, movies, travel, health tips, or advice. "
    "If the user uploads a dataset, you can also analyze it; you may mention this capability briefly if relevant. "
    "Never claim you cannot access files or data; simply provide helpful answers. "
    "Keep responses clear, concrete, and in 2–5 sentences."
)


@app.post("/signup")
def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(username=username, email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    return {"msg": "User created successfully"}

@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


def _maybe_require_user(token_user = Depends(get_current_user)):
    """
    If REQUIRE_AUTH=True, this dependency enforces JWT on protected routes.
    If REQUIRE_AUTH=False, we allow anonymous by returning None.
    """
    return token_user if REQUIRE_AUTH else None

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    _user = Depends(_maybe_require_user)
):
    """
    Accept CSV / Excel / PDF and store the DataFrame on disk with a new dataset_id.
    Returns dataset_id + detected columns.
    """
    content = await file.read()
    df, kind = read_any(content, file.filename)
    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="No tabular data found")
    ds_id = uuid.uuid4().hex[:12]
    save_df(ds_id, df)
    return {"dataset_id": ds_id, "type": kind, "columns": df.columns.tolist()}

@app.post("/ask")
async def ask(
    payload: dict,
    _user = Depends(_maybe_require_user)
):
    """
    If dataset_id is missing -> general chat.
    If dataset_id present -> NL → SQL → DuckDB → narrated answer.
    """
    ds = payload.get("dataset_id")
    q = (payload.get("query") or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    
    if not ds:
        llm = ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            model="mistralai/mixtral-8x7b-instruct",
            temperature=0.7,
        )
        out = llm.invoke([SystemMessage(content=CHAT_SYS), HumanMessage(content=q)])
        return JSONResponse({"answer": out.content})

    
    df = load_df(ds)
    if df is None:
        raise HTTPException(status_code=404, detail="dataset_id not found")

    
    sql = make_sql(q, df)
    print("SQL:", sql)  

    
    res_df, final_sql = run_sql_with_retry(df, sql, lambda s, e: rewrite_sql_bad(s, e, df))

   
    if "smalltalk" in res_df.columns:
        llm = ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            model="mistralai/mixtral-8x7b-instruct",
            temperature=0.7,
        )
        out = llm.invoke([SystemMessage(content=CHAT_SYS), HumanMessage(content=q)])
        return JSONResponse({"answer": out.content})

    
    rows = res_df.to_dict(orient="records")
    if res_df.shape == (1, 1):
        
        val = list(rows[0].values())[0]
        text = narrate(q, final_sql, {"value": val})
    else:
        text = narrate(q, final_sql, rows[:50]) 

    return JSONResponse({
        "answer": text,
        "rows": make_json_safe(rows[:200]),
        "sql": final_sql
    })
