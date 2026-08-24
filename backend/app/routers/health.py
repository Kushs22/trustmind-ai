import os
from pathlib import Path

from fastapi import APIRouter

from app.config import database_url_safe_summary, settings

router = APIRouter(tags=["health"])

# Bump when production KB / RAG behaviour must be verifiable after deploy.
APP_VERSION = "1.2.3"
RELEASE_NOTE = (
    "Literature PDF sources in BM25 KB (LIT_*) + health KB fingerprint for deploy checks"
)


def _kb_fingerprint(repo_root: Path) -> dict[str, object]:
    """Lightweight KB stats so we can confirm Render deployed the latest index."""
    chunks_path = repo_root / "knowledge_base" / "chunks" / "chunks.jsonl"
    bm25_path = repo_root / "knowledge_base" / "indexes" / "bm25" / "bm25.pkl"
    total = 0
    lit = 0
    if chunks_path.is_file():
        try:
            with chunks_path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    total += 1
                    if '"source_id": "LIT_' in line or '"source_id":"LIT_' in line:
                        lit += 1
        except OSError:
            pass
    return {
        "chunks_jsonl_exists": chunks_path.is_file(),
        "chunks_total": total,
        "lit_chunks": lit,
        "bm25_bytes": bm25_path.stat().st_size if bm25_path.is_file() else 0,
        "git_commit": (os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "")[:12],
        "git_branch": os.getenv("RENDER_GIT_BRANCH") or "",
    }


def _pipeline_diagnostics() -> dict[str, object]:
    """Safe import/path checks for Render debugging (no OpenAI calls)."""
    from app.services.llm_pipeline import _REPO_ROOT, _ensure_paths as _llm_paths

    repo_root = _REPO_ROOT
    faiss_path = repo_root / "knowledge_base" / "indexes" / "faiss" / "index.faiss"
    bm25_path = repo_root / "knowledge_base" / "indexes" / "bm25" / "bm25.pkl"
    out: dict[str, object] = {
        "repo_root": str(repo_root),
        "faiss_index_exists": faiss_path.is_file(),
        "bm25_index_exists": bm25_path.is_file(),
        "kb": _kb_fingerprint(repo_root),
        "rag_import_ok": False,
        "llm_baseline_import_ok": False,
        "llm_pipeline_local_helpers_ok": False,
        "openai_package_ok": False,
        "import_error": "",
    }
    try:
        import openai  # noqa: F401

        out["openai_package_ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["import_error"] = f"openai: {type(exc).__name__}: {exc}"
        return out

    try:
        from app.services.rag_pipeline_service import _ensure_paths as _rag_paths

        _rag_paths()
        import rag.config  # noqa: F401

        out["rag_import_ok"] = True
    except Exception as exc:  # noqa: BLE001
        out["import_error"] = f"rag: {type(exc).__name__}: {exc}"

    try:
        _llm_paths()
        import llm_baseline  # noqa: F401

        out["llm_baseline_import_ok"] = True
    except Exception as exc:  # noqa: BLE001
        prev = str(out.get("import_error") or "")
        extra = f"llm_baseline: {type(exc).__name__}: {exc}"
        out["import_error"] = f"{prev} | {extra}" if prev else extra

    try:
        from app.services.llm_pipeline import (  # noqa: F401
            _call_openai_json_local,
            _parse_prediction_local,
        )

        out["llm_pipeline_local_helpers_ok"] = True
    except Exception as exc:  # noqa: BLE001
        prev = str(out.get("import_error") or "")
        extra = f"llm_local: {type(exc).__name__}: {exc}"
        out["import_error"] = f"{prev} | {extra}" if prev else extra

    return out

@router.get("/health")
def health_check() -> dict[str, object]:
    """Liveness + safe config diagnostics (no secrets)."""
    return {
        "status": "ok",
        "service": "trustmind-ai-backend",
        "version": APP_VERSION,
        "release_note": RELEASE_NOTE,
        "database": database_url_safe_summary(settings.database_url),
        "database_is_sqlite": settings.is_sqlite,
        "database_is_postgres": settings.is_postgres,
        "openai_configured": bool(settings.openai_api_key),
        "openai_model": settings.openai_model,
        "groq_configured": bool(settings.groq_api_key),
        "groq_model": settings.groq_model,
        "gemini_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "llm_provider": settings.llm_provider,
        "use_rag": settings.use_rag,
        "enable_abstention": settings.enable_abstention,
        "enable_confidence_calibration": settings.enable_confidence_calibration,
        "consistency_runs": settings.consistency_runs,
        "confidence_threshold": settings.confidence_threshold,
        "grounding_retrieval_quality_min": settings.grounding_retrieval_quality_min,
        "grounding_evidence_strength_min": settings.grounding_evidence_strength_min,
        "analyse_backend": settings.analyse_backend,
        "pipeline": _pipeline_diagnostics(),
    }
