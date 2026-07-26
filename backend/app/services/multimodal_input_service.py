"""Normalise multimodal user inputs into labelled combined text for analyse."""

from __future__ import annotations

from app.schemas.analyse import AnalyseRequest
from app.schemas.multimodal import (
    AttachmentContext,
    InputSourceItem,
    InputSummaryOut,
    NormalisedMultimodalInput,
    ProcessedAttachmentOut,
)


def build_labelled_combined_text(
    *,
    typed_text: str,
    speech_transcript: str,
    image_contexts: list[AttachmentContext],
    pdf_contexts: list[AttachmentContext],
) -> str:
    """
    Build clearly labelled combined user text.

    User uploads are contextual input only — never trusted RAG evidence.
    """
    sections: list[str] = []
    typed = (typed_text or "").strip()
    spoken = (speech_transcript or "").strip()
    if typed:
        sections.append(f"Typed input:\n{typed}")
    if spoken:
        sections.append(f"Spoken input:\n{spoken}")
    for img in image_contexts:
        if not img.included:
            continue
        body = (img.extracted_text or img.summary or "").strip()
        if not body:
            continue
        label = img.filename or "image"
        sections.append(f"Text extracted from image ({label}):\n{body}")
    for pdf in pdf_contexts:
        if not pdf.included:
            continue
        body = (pdf.extracted_text or pdf.summary or "").strip()
        if not body:
            continue
        label = pdf.filename or "document"
        sections.append(f"Text extracted from PDF ({label}):\n{body}")
    return "\n\n".join(sections).strip()


def normalize_multimodal_input(request: AnalyseRequest) -> NormalisedMultimodalInput:
    """
    Merge typed / speech / confirmed attachment text into one analyse string.

    Backward compatible: if only `text` is set, use it as typed input.
    """
    typed = (request.typed_text or "").strip()
    legacy = (request.text or "").strip()
    if not typed and legacy:
        # Avoid double-counting when client sends both as the same content
        typed = legacy

    speech = (request.speech_transcript or "").strip()
    images = list(request.image_context or [])
    pdfs = list(request.pdf_context or [])

    included_images = [i for i in images if i.included and (i.extracted_text or i.summary)]
    included_pdfs = [p for p in pdfs if p.included and (p.extracted_text or p.summary)]

    combined = build_labelled_combined_text(
        typed_text=typed,
        speech_transcript=speech,
        image_contexts=images,
        pdf_contexts=pdfs,
    )
    if not combined and legacy:
        combined = legacy

    sources: list[InputSourceItem] = []
    if typed:
        sources.append(InputSourceItem(type="typed_text", included=True))
    if speech:
        sources.append(InputSourceItem(type="speech_transcript", included=True))
    for img in images:
        sources.append(
            InputSourceItem(
                type="image",
                included=bool(img.included and (img.extracted_text or img.summary)),
                filename=img.filename or None,
            )
        )
    for pdf in pdfs:
        sources.append(
            InputSourceItem(
                type="pdf",
                included=bool(pdf.included and (pdf.extracted_text or pdf.summary)),
                filename=pdf.filename or None,
            )
        )

    attachments: list[ProcessedAttachmentOut] = []
    for img in images:
        attachments.append(
            ProcessedAttachmentOut(
                type="image",
                filename=img.filename or "image",
                status="processed",
                included_in_analysis=bool(
                    img.included and (img.extracted_text or img.summary)
                ),
                warnings=list(img.warnings or []),
            )
        )
    for pdf in pdfs:
        attachments.append(
            ProcessedAttachmentOut(
                type="pdf",
                filename=pdf.filename or "document.pdf",
                status="processed",
                included_in_analysis=bool(
                    pdf.included and (pdf.extracted_text or pdf.summary)
                ),
                warnings=list(pdf.warnings or []),
            )
        )

    summary = InputSummaryOut(
        typed_text_used=bool(typed),
        speech_transcript_used=bool(speech),
        image_count=len(included_images),
        pdf_count=len(included_pdfs),
    )

    user_context = {
        "typed_text": typed,
        "speech_transcript": speech,
        "image_context": [i.model_dump() for i in images],
        "pdf_context": [p.model_dump() for p in pdfs],
    }

    return NormalisedMultimodalInput(
        combined_user_text=combined,
        typed_text=typed,
        speech_transcript=speech,
        input_sources=sources,
        input_summary=summary,
        processed_attachments=attachments,
        user_context=user_context,
    )
