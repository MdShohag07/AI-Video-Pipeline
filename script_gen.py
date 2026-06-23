"""
Step 1: turn one topic into a narration script + a matching list of AI-image
prompts, using pollinations.ai's free text model (no signup, no API key).
"""

import json
import re
import urllib.parse

import requests

import config


def _extract_json(raw_text: str) -> dict:
    """
    The free text model usually returns clean JSON, but it sometimes wraps it
    in ```json fences or adds a stray sentence before/after. This pulls out
    the first {...} block so a little chatter doesn't break the pipeline.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in the model's reply:\n\n{raw_text}")
    return json.loads(match.group(0))


def generate_script(topic: str, num_scenes: int = None) -> dict:
    """
    Asks pollinations.ai to write a short-form video script about `topic`,
    already split into segments so each one maps 1:1 to a narration clip and
    a scene image — this is what lets the final video sync exactly instead
    of guessing how long each scene should be.

    Returns a dict shaped like:
        {
          "segments": [
            {"narration": "first short line of the script", "image_prompt": "..."},
            {"narration": "second short line of the script", "image_prompt": "..."},
            ...
          ]
        }
    """
    num_scenes = num_scenes or config.NUM_SCENES

    instruction = (
        f"Write a short-form vertical video script about: {topic}\n\n"
        "Rules:\n"
        "- Hook in the very first segment. No slow intro, no 'hey guys'.\n"
        "- Plain spoken language, like you're talking to one person.\n"
        "- No emojis, no stage directions, no hashtags inside the narration.\n"
        f"- Split the script into exactly {num_scenes} short segments "
        "(roughly one sentence or idea each, a few seconds of speech).\n"
        "- For every segment, also write a short stock-photo SEARCH QUERY "
        "(3-5 plain keywords, not a full descriptive sentence) that would "
        "find a real matching photo on a stock library — e.g. "
        "'rickshaw dhaka street rain', not 'a cinematic shot of a rickshaw "
        "in the rain'. Don't mention real people's names.\n"
        "- Also suggest ONE short background ambience/mood for the whole "
        "video, 1-3 words, only if something genuinely fits — e.g. 'soft "
        "rain', 'ocean waves', 'calm lo-fi piano', 'upbeat ukulele'. If "
        "nothing natural fits the topic, just write 'none'.\n\n"
        "- Also write a short punchy TITLE for the whole video (3-6 words, "
        "Title Case or CAPS, hook-y) with exactly ONE relevant emoji at the "
        "very start — e.g. '⚽ GERMANY'S FOOTBALL LEGACY', '🌧️ THE SOUND OF "
        "RAIN'.\n\n"
        "Return ONLY valid JSON, nothing before or after it, in exactly "
        "this shape:\n"
        "{\n"
        '  "title": "<emoji> <SHORT PUNCHY TITLE>",\n'
        '  "background_mood": "<1-3 word ambience, or \\"none\\">",\n'
        '  "segments": [\n'
        '    {"narration": "<segment 1 text>", "image_prompt": "<segment 1 image prompt>"},\n'
        '    {"narration": "<segment 2 text>", "image_prompt": "<segment 2 image prompt>"}\n'
        "  ]\n"
        "}"
    )

    encoded = urllib.parse.quote(instruction)
    url = f"{config.POLLINATIONS_TEXT_URL}/{encoded}"
    params = {"model": config.TEXT_MODEL} if config.TEXT_MODEL else {}
    headers = {"Authorization": f"Bearer {config.POLLINATIONS_API_KEY}"} if config.POLLINATIONS_API_KEY else {}

    response = requests.get(url, params=params, headers=headers, timeout=60)
    if not response.ok:
        raise RuntimeError(
            f"pollinations.ai text request failed ({response.status_code}). "
            f"Response body: {response.text[:500]}"
        )

    data = _extract_json(response.text)

    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError(f"Script came back in an unexpected shape: {data}")
    for seg in segments:
        if "narration" not in seg or "image_prompt" not in seg:
            raise ValueError(f"Segment missing narration/image_prompt: {seg}")

    return data


if __name__ == "__main__":
    # Quick manual test: python script_gen.py "your topic here"
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "why the sky is blue"
    result = generate_script(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
