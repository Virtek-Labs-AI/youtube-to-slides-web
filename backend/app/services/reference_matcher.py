"""Match slide bullets to YouTube transcript timestamps using an LLM.

After Presenton generates a styled PPTX, this module extracts the slide text
and uses GPT-4o-mini to match each bullet to the best transcript timestamp.
"""

import json

import structlog
from openai import OpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are matching PowerPoint slide bullets to YouTube video timestamps.

The slides were AI-generated from a video transcript, so bullet text is paraphrased — it will NOT match the transcript verbatim. You must match by meaning and context, not keywords.

INSTRUCTIONS:
1. Read the FULL transcript to understand the chronological flow of topics.
2. For each slide, identify its overall topic from the title and bullets together.
3. Find the SECTION of the transcript where that topic is discussed. Topics follow the video's chronological order — use this to narrow your search.
4. For each bullet on that slide, find the specific moment where that point is FIRST introduced or most clearly stated within that section.
5. Use the url from the transcript sentence at that moment.

RULES:
- Prefer the timestamp where a topic BEGINS being discussed, not where it's summarized or concluded.
- Two bullets on the same slide should generally map to different timestamps within the same topic section.
- If a bullet synthesizes multiple transcript sentences, link to where the core idea first appears.
- Only include bullets that have a clear contextual match. Skip title slides and bullets with no meaningful transcript correspondence.

Output ONLY a JSON array. Each entry:
- slide: 0-indexed slide number
- bullet: 0-indexed bullet index within that slide
- url: the url from the best-matching transcript sentence

Output ONLY the JSON array, no markdown fences, no commentary."""


def match_references(
    transcript: list[dict], slides_content: list[dict]
) -> list[dict]:
    """Use GPT-4o-mini to match slide bullets to transcript timestamps.

    Args:
        transcript: List of transcript segments with text and url fields.
        slides_content: Extracted slide data from slide_extractor.extract_slides().

    Returns:
        List of reference dicts: [{"slide": int, "bullet": int, "url": str}]
    """
    transcript_text = json.dumps(transcript, indent=2)
    slides_text = json.dumps(slides_content, indent=2)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"TRANSCRIPT:\n{transcript_text}\n\nSLIDES:\n{slides_text}",
            },
        ],
    )

    raw = (response.choices[0].message.content or "").strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    references = json.loads(raw)
    logger.info("reference_matching_complete", n_references=len(references))
    return references
