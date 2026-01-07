# mcp_server.py

import sqlite3
import json
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends, status
from pydantic import BaseModel
import uvicorn
from mlflow_logger import log_mcp_run
import time

DB_PATH = r"mcp_demo.db"

# ---------------- AUTH SETUP ----------------

SECRET_KEY = os.getenv("MCP_SECRET_KEY", "1234")


def verify_auth(authorization: str = Header(None)):
    if SECRET_KEY is None:
        raise HTTPException(
            status_code=500, detail="Server auth misconfigured: MCP_SECRET_KEY not set"
        )

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = authorization.split("Bearer ")[1].strip()

    if token != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token",
        )

    return True


# ---------------- DB INIT ----------------


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
        title TEXT,
        body TEXT
        )
    """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS query (
        title TEXT,
        body TEXT
        )
    """
    )

    conn.commit()
    conn.close()


init_db()

app = FastAPI(title="Minimal MCP Server (With Auth)")


# -------------- JSON-RPC MODELS --------------


class JsonRpcRequest(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


# -------------- MCP TOOLS METADATA --------------

TOOLS_METADATA = [
    {
        "name": "query",
        "description": "Run a safe SELECT query on notes or query tables.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "enum": ["notes", "query"]},
                "limit": {"type": "integer"},
            },
            "required": ["table"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "rows": {"type": "array"},
                "columns": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "insert_query",
        "description": "Insert a record into the query table.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title"],
        },
        "output_schema": {"type": "object", "properties": {"id": {"type": "integer"}}},
    },
    {
        "name": "insert_note",
        "description": "Insert a record into the notes table.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title"],
        },
        "output_schema": {"type": "object", "properties": {"id": {"type": "integer"}}},
    },
    {
        "name": "list_tables",
        "description": "List all database tables.",
        "input_schema": {"type": "object"},
        "output_schema": {
            "type": "object",
            "properties": {"tables": {"type": "array", "items": {"type": "string"}}},
        },
    },
]


# -------------- MCP ENDPOINT WITH AUTH --------------


@app.post("/mcp")
async def handle_mcp(request: Request, auth=Depends(verify_auth)):
    start = time.time()
    tool = "unknown"
    params = {}

    try:
        data = await request.json()

        method = data.get("method")
        params = data.get("params", {})
        tool = params.get("tool")
        request_id = data.get("id")

        if method != "call":
            raise ValueError("Method not found")

        if tool not in ["insert_note", "insert_query", "query", "list_tables"]:
            raise ValueError("Tool not found")

        # ---------- INSERT NOTE ----------
        if tool == "insert_note":
            title = params.get("title")
            body = params.get("body")

            if not title:
                raise ValueError("title is required")

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO notes (title, body) VALUES (?, ?)", (title, body))
            conn.commit()
            inserted_id = cur.lastrowid
            conn.close()

            result = {"id": inserted_id}

        # ---------- INSERT QUERY ----------
        elif tool == "insert_query":
            title = params.get("title")
            body = params.get("body")

            if not title:
                raise ValueError("title is required")

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO query (title, body) VALUES (?, ?)", (title, body))
            conn.commit()
            inserted_id = cur.lastrowid
            conn.close()

            result = {"id": inserted_id}

        # ---------- LIST TABLES ----------
        elif tool == "list_tables":
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            result = {"tables": [r[0] for r in cur.fetchall()]}
            conn.close()

        # ---------- QUERY ----------
        elif tool == "query":
            table = params.get("table")
            limit = params.get("limit", 50)

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))
            rows = cur.fetchall()
            columns = [c[0] for c in cur.description]
            conn.close()

            result = {"rows": rows, "columns": columns}

        latency = time.time() - start

        log_mcp_run(
            tool=tool,
            latency=latency,
            request_payload=params,
            response_payload=result,
            status="success",
        )

        return {"jsonrpc": "2.0", "result": result, "id": request_id}

    except Exception as e:
        latency = time.time() - start

        log_mcp_run(
            tool=tool,
            latency=latency,
            request_payload=params,
            status="error",
            error=str(e),
        )

        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": data.get("id") if isinstance(data, dict) else None,
        }
