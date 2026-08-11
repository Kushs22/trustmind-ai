from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


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
        "version": "1.2.1",
        "release_note": "LLM-only GroundingInfo/resolve_grounding fix + self-contained LLM pipeline",
        "openai_configured": bool(settings.openai_api_key),
        "openai_model": settings.openai_model,
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
