import mlflow
import json
import time
import os
from typing import Optional, Dict, Any

# ---------------- MLflow CONFIG ----------------
mlflow.set_tracking_uri("file:./mlruns")
mlflow.set_experiment("mcp_server")


def log_mcp_run(
    *,
    tool: str,
    latency: float,
    request_payload: Optional[Dict[str, Any]] = None,
    response_payload: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error: Optional[str] = None,
    model_name: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
):
    """
    Logs ALL meaningful MCP + LLM metrics to MLflow
    """

    request_payload = request_payload or {}
    response_payload = response_payload or {}

    request_json = json.dumps(request_payload)
    response_json = json.dumps(response_payload)

    input_size = len(request_json.encode("utf-8"))
    output_size = len(response_json.encode("utf-8"))

    with mlflow.start_run(nested=True):

        # ---------- TAGS ----------
        mlflow.set_tag("tool", tool)
        mlflow.set_tag("status", status)
        mlflow.set_tag("service", "mcp")
        mlflow.set_tag("environment", os.getenv("ENV", "local"))

        if model_name:
            mlflow.set_tag("model", model_name)

        if error:
            mlflow.set_tag("error", error)

        # ---------- PARAMETERS ----------
        mlflow.log_param("tool_name", tool)
        mlflow.log_param("has_llm", model_name is not None)

        # ---------- CORE METRICS ----------
        mlflow.log_metric("latency_sec", latency)
        mlflow.log_metric("request_size_bytes", input_size)
        mlflow.log_metric("response_size_bytes", output_size)

        # ---------- TOOL METRICS ----------
        mlflow.log_metric("request_count", 1)
        mlflow.log_metric("error_count", 0 if status == "success" else 1)

        # ---------- CONTENT METRICS ----------
        mlflow.log_metric("response_length_chars", len(response_json))

        if input_size > 0:
            compression_ratio = output_size / input_size
            mlflow.log_metric("compression_ratio", compression_ratio)

        # ---------- LLM METRICS (OPTIONAL) ----------
        if input_tokens is not None:
            mlflow.log_metric("input_tokens", input_tokens)

        if output_tokens is not None:
            mlflow.log_metric("output_tokens", output_tokens)
            mlflow.log_metric(
                "total_tokens",
                (input_tokens or 0) + output_tokens
            )

        # ---------- ARTIFACTS ----------
        mlflow.log_text(request_json, "request.json")
        mlflow.log_text(response_json, "response.json")
