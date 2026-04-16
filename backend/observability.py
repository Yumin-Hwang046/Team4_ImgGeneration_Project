import base64
import mimetypes
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

_wandb = None
_wandb_inited = False
_langfuse = None

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")
load_dotenv(_BASE_DIR.parent / ".env")


def _has_langfuse_env() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def get_wandb():
    global _wandb, _wandb_inited
    if _wandb is None:
        try:
            import wandb as _wb
            _wandb = _wb
        except Exception:
            _wandb = False

    if _wandb is False:
        return None
    if not os.getenv("WANDB_API_KEY"):
        return None

    if not _wandb_inited:
        _wandb.init(
            project=os.getenv("WANDB_PROJECT", "imggen"),
            entity=os.getenv("WANDB_ENTITY") or None,
        )
        _wandb_inited = True
    return _wandb


def get_langfuse():
    global _langfuse
    if _langfuse is None:
        try:
            from langfuse import Langfuse
            _langfuse = Langfuse()
        except Exception:
            _langfuse = False

    if _langfuse is False:
        return None
    if not _has_langfuse_env():
        return None
    return _langfuse


def log_wandb(event: str, data: dict[str, Any]) -> None:
    wb = get_wandb()
    if not wb:
        return
    payload = {"event": event, **data}
    wb.log(payload)


def to_wandb_image(path: str, caption: Optional[str] = None):
    wb = get_wandb()
    if not wb:
        return None

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None

    try:
        return wb.Image(str(file_path), caption=caption)
    except Exception:
        return None


def to_langfuse_media(path: str) -> Optional[str]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None

    try:
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception:
        return None


def log_langfuse_trace(
    name: str,
    input: dict[str, Any],
    output: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
) -> None:
    lf = get_langfuse()
    if not lf:
        return
    try:
        lf.trace(
            name=name,
            input=input,
            output=output,
            metadata=metadata,
            tags=tags,
        )
    except Exception:
        return
