"""
Optional step: finds a free background ambience/mood track that matches the
video's topic — e.g. soft rain sounds for a video about rain — using
Freesound.org, a long-running free sound library (not a metered AI service,
so it doesn't carry the rate-limit surprises pollinations.ai gave us).

This step is designed to fail safely everywhere: if there's no API key, no
matching sound, or a network hiccup, it just returns None and the rest of
the pipeline continues making the video without background sound, instead
of breaking the whole run over a nice-to-have.
"""

from typing import Optional

import requests

import config


def find_background_track(mood_query: str, out_path: str) -> Optional[str]:
    """
    Searches Freesound for a track matching `mood_query` and saves the best
    match's preview audio to `out_path`.

    Returns `out_path` on success, or None if nothing usable was found —
    callers should treat None as "just skip background music."
    """
    if not config.FREESOUND_API_KEY:
        print("  (no FREESOUND_API_KEY set — skipping background music)")
        return None

    if not mood_query or mood_query.strip().lower() in ("none", "n/a", ""):
        print("  (script didn't suggest a background mood — skipping background music)")
        return None

    headers = {"Authorization": f"Token {config.FREESOUND_API_KEY}"}
    params = {
        "query": mood_query,
        "fields": "id,name,previews,duration",
        "filter": "duration:[5 TO 180]",  # skip very short stings or huge files
        "page_size": 5,
    }

    try:
        response = requests.get(
            config.FREESOUND_SEARCH_URL, headers=headers, params=params, timeout=30
        )
        if not response.ok:
            print(f"  (Freesound search failed [{response.status_code}] — skipping background music)")
            return None

        results = response.json().get("results", [])
        if not results:
            print(f"  (no Freesound match for {mood_query!r} — skipping background music)")
            return None

        preview_url = results[0].get("previews", {}).get("preview-hq-mp3")
        if not preview_url:
            print("  (matched sound had no usable preview — skipping background music)")
            return None

        audio_response = requests.get(preview_url, timeout=60)
        audio_response.raise_for_status()

        with open(out_path, "wb") as f:
            f.write(audio_response.content)

        print(f"  background track found: {results[0].get('name', mood_query)!r}")
        return out_path

    except Exception as e:
        print(f"  (background music step failed ({e}) — continuing without it)")
        return None


if __name__ == "__main__":
    # Quick manual test: python music_gen.py
    result = find_background_track("soft rain", "test_music.mp3")
    print("Result:", result)
