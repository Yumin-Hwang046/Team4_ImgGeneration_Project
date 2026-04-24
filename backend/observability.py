import base64
import mimetypes
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

_wandb = None
_wandb_inited = False
_langfuse = None
_status_printed = False

_BASE_DIR = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")
load_dotenv(_BASE_DIR.parent / ".env")


def _has_langfuse_env() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _probe_wandb() -> None:
    global _wandb
    if _wandb is None:
        try:
            import wandb as _wb

            _wandb = _wb
        except Exception:
            _wandb = False


def _probe_langfuse() -> None:
    global _langfuse
    if _langfuse is None:
        try:
            from langfuse import Langfuse

            _langfuse = Langfuse()
        except Exception:
            _langfuse = False


def _print_status_once() -> None:
    global _status_printed
    if _status_printed:
        return

    _probe_langfuse()
    _probe_wandb()

    langfuse_env = _has_langfuse_env()
    langfuse_installed = _langfuse is not False
    wandb_env = bool(os.getenv("WANDB_API_KEY"))
    wandb_installed = _wandb is not False

    print(
        "[observability] "
        f"langfuse_env={langfuse_env} "
        f"langfuse_installed={langfuse_installed} "
        f"langfuse_enabled={langfuse_env and langfuse_installed} "
        f"wandb_env={wandb_env} "
        f"wandb_installed={wandb_installed} "
        f"wandb_enabled={wandb_env and wandb_installed}"
    )
    if langfuse_env and not langfuse_installed:
        print("[observability] Langfuse env is set, but `langfuse` package is not installed.")
    if wandb_env and not wandb_installed:
        print("[observability] W&B env is set, but `wandb` package is not installed.")

    _status_printed = True


def get_wandb():
    global _wandb, _wandb_inited
    _probe_wandb()
    _print_status_once()

    if _wandb is False:
        return None
    if not os.getenv("WANDB_API_KEY"):
        return None

    if not _wandb_inited:
        try:
            _wandb.init(
                project=os.getenv("WANDB_PROJECT", "imggen"),
                entity=os.getenv("WANDB_ENTITY") or None,
            )
            _wandb_inited = True
        except Exception as exc:
            print(f"[observability] W&B init failed: {type(exc).__name__}: {exc}")
            return None
    return _wandb


def get_langfuse():
    _probe_langfuse()
    _print_status_once()

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


def build_langfuse_media_list(paths: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in paths:
        items.append(
            {
                "path": path,
                "media": to_langfuse_media(path),
            }
        )
    return items


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
    except Exception as exc:
        print(f"[observability] Langfuse trace failed: {type(exc).__name__}: {exc}")


def report_observability_status() -> dict[str, bool]:
    _probe_langfuse()
    _probe_wandb()
    _print_status_once()
    return {
        "langfuse_env": _has_langfuse_env(),
        "langfuse_installed": _langfuse is not False,
        "langfuse_enabled": _has_langfuse_env() and _langfuse is not False,
        "wandb_env": bool(os.getenv("WANDB_API_KEY")),
        "wandb_installed": _wandb is not False,
        "wandb_enabled": bool(os.getenv("WANDB_API_KEY")) and _wandb is not False,
    }


if __name__ == "__main__":
    print(report_observability_status())
