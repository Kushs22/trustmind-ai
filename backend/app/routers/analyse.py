from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User
from app.schemas.analyse import AnalyseRequest, AnalyseResponse
from app.services.check_in_service import analyse_and_optionally_save

router = APIRouter(tags=["analyse"])

ANALYSE_DESCRIPTION = """
Run a trustworthy wellbeing assessment.

**Pipelines** (selected per request via `pipeline_mode`, else server `USE_RAG`):
- `pipeline_mode: "llm"` → standalone LLM (`pipeline_used: "LLM"`)
- `pipeline_mode: "rag"` → hybrid BM25+FAISS RAG (`pipeline_used: "LLM+RAG"`)
- `pipeline_mode: "auto"` → honour server `USE_RAG`

The frontend never calls the LLM directly.

**Abstention:** if confidence &lt; `CONFIDENCE_THRESHOLD` (default 0.75) and
`ENABLE_ABSTENTION=true`, the API returns `status: "abstained"` with
`prediction: null` and a support recommendation.

**High-risk:** when the prediction is `SuicideWatch` (or crisis sources are
retrieved), `support_resources` lists NHS / Samaritans / Student Minds / UWE links.
These are support services — not a diagnosis.
"""


@router.post(
    "/api/v1/analyse",
    response_model=AnalyseResponse,
    summary="Analyse wellbeing text",
    description=ANALYSE_DESCRIPTION,
    responses={
        200: {
            "description": "Successful analysis (accepted or abstained)",
            "content": {
                "application/json": {
                    "examples": {
                        "llm_accepted": {
                            "summary": "LLM accepted prediction",
                            "value": {
                                "status": "accepted",
                                "prediction": "Anxiety",
                                "confidence": 0.91,
                                "reasoning": "Language emphasises worry and physical tension.",
                                "sources": [],
                                "pipeline_used": "LLM",
                                "concern_level": "Moderate",
                                "ai_confidence": "91%",
                                "explanation": "Language emphasises worry and physical tension.",
                                "safe_next_steps": [
                                    "Consider speaking to someone you trust"
                                ],
                                "safety_note": "This tool provides wellbeing support information...",
                                "saved_to_history": False,
                            },
                        },
                        "rag_accepted": {
                            "summary": "LLM+RAG accepted prediction",
                            "value": {
                                "status": "accepted",
                                "prediction": "depression",
                                "confidence": 0.88,
                                "reasoning": "Aligned with NHS low-mood guidance retrieved.",
                                "sources": ["NHS_DEP_001", "NHS_EMM_LOWMOOD_001"],
                                "pipeline_used": "LLM+RAG",
                                "support_resources": [],
                                "saved_to_history": False,
                            },
                        },
                        "abstained": {
                            "summary": "Abstention (low confidence)",
                            "value": {
                                "status": "abstained",
                                "prediction": None,
                                "confidence": 0.61,
                                "reasoning": (
                                    "The model is not sufficiently confident to provide "
                                    "a reliable wellbeing assessment."
                                ),
                                "message": (
                                    "The model is not sufficiently confident to provide "
                                    "a reliable wellbeing assessment."
                                ),
                                "recommendation": (
                                    "Consider contacting your GP, NHS services or your "
                                    "university wellbeing team if you require support."
                                ),
                                "sources": [],
                                "pipeline_used": "LLM",
                                "abstention_status": (
                                    "Abstention triggered — no clinical prediction"
                                ),
                                "saved_to_history": False,
                            },
                        },
                    }
                }
            },
        }
    },
)
@router.post(
    "/api/analyse",
    response_model=AnalyseResponse,
    include_in_schema=True,
    summary="Analyse wellbeing text (alias)",
    description="Alias of `/api/v1/analyse` for clients that call `/api/analyse`.",
)
def analyse(
    payload: AnalyseRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> AnalyseResponse:
    try:
        return analyse_and_optionally_save(db, payload, user)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
