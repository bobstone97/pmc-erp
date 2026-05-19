import uuid
from pathlib import Path

import streamlit as st

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads" / "expenses"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def save_expense_attachment(uploaded_file, category: str) -> str | None:
    if uploaded_file is None:
        return None
    ext = Path(uploaded_file.name).suffix or ""
    safe_name = f"{category}_{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_ROOT / safe_name
    dest.write_bytes(uploaded_file.getvalue())
    return f"uploads/expenses/{safe_name}"


def attachment_download_button(path: str | None, key: str):
    if not path:
        return
    full = Path(__file__).resolve().parent.parent / path
    if full.exists():
        st.download_button(
            "Download proof",
            full.read_bytes(),
            file_name=full.name,
            key=key,
            mime="application/octet-stream",
        )
