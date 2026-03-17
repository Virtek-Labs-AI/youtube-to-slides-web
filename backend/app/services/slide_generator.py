import yaml
from openai import OpenAI

from app.core.config import settings

SYSTEM_PROMPT = """You are a presentation expert. Given a YouTube video \
transcript with timestamps, create a structured slide deck in YAML format.

Rules:
- Each bullet point must be 10 words or fewer.
- Include the YouTube timestamp URL after each bullet referencing specific content.
- The YAML must follow this exact structure.

Output ONLY valid YAML with this structure (no markdown fences, no commentary):

slides:
  - type: title
    title: "Presentation Title"
    subtitle: "Based on the video content"
  - type: overview
    title: "Overview"
    bullets:
      - text: "First key topic"
      - text: "Second key topic"
  - type: content
    title: "Slide Title"
    bullets:
      - text: "Key point in 10 words or fewer"
        url: "https://youtu.be/VIDEO_ID?t=SECONDS"
      - text: "Another key point"
        url: "https://youtu.be/VIDEO_ID?t=SECONDS"
  - type: takeaway
    title: "Key Takeaways"
    bullets:
      - text: "Main takeaway one"
      - text: "Main takeaway two"

Create 8-15 slides total. Group related transcript segments into coherent slides."""


def generate_slides_from_transcript(transcript: list[dict], video_id: str) -> dict:
    transcript_text = _format_transcript(transcript)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Create a slide deck from this transcript of YouTube video {video_id}.\n\n"
                    f"Transcript:\n{transcript_text}"
                ),
            },
        ],
    )

    raw_yaml = (response.choices[0].message.content or "").strip()
    # Strip markdown fences if present
    if raw_yaml.startswith("```"):
        lines = raw_yaml.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_yaml = "\n".join(lines)

    slides_data = yaml.safe_load(raw_yaml)
    return slides_data


def format_slides_as_markdown(slides_data: dict) -> list[str]:
    """Convert slide outline to Presenton's slides_markdown format.

    Each slide becomes one markdown string. Bullets with URLs are rendered as
    markdown links so Presenton can attempt to preserve them as hyperlinks.
    """
    result: list[str] = []
    for slide in slides_data.get("slides", []):
        title = slide.get("title", "")
        bullets = slide.get("bullets", [])
        lines = [f"# {title}"]
        for b in bullets:
            if not isinstance(b, dict):
                lines.append(f"- {b}")
                continue
            text = b.get("text", "")
            url = b.get("url", "")
            if url:
                lines.append(f"- [{text}]({url})")
            else:
                lines.append(f"- {text}")
        result.append("\n".join(lines))
    return result


def _format_transcript(transcript: list[dict]) -> str:
    lines: list[str] = []
    for seg in transcript:
        minutes = int(seg["start"] // 60)
        seconds = int(seg["start"] % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg['text']} ({seg['url']})")
    return "\n".join(lines)
