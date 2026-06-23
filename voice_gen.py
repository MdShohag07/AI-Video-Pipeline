"""
Step 2: turn narration text into voice (.mp3) plus word-level timing, using
Microsoft Edge's free neural voices via edge-tts. No API key, runs locally.

This generates audio one segment at a time (instead of one giant narration)
so every scene's exact duration is known instead of estimated — that's what
lets the final video line up perfectly with no guesswork.
"""

import asyncio
from datetime import timedelta
from typing import List

import edge_tts
from edge_tts.srt_composer import Subtitle, compose

import config

WORDS_PER_CAPTION = 4  # short phrase chunks read better than single flickering words


async def _synthesize(text: str, audio_path: str) -> List[Subtitle]:
    communicate = edge_tts.Communicate(
        text,
        config.VOICE,
        rate=config.SPEECH_RATE,
        boundary="WordBoundary",
    )
    submaker = edge_tts.SubMaker()

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    return submaker.cues


def synthesize_segment(text: str, audio_path: str) -> List[Subtitle]:
    """
    Writes `text` as speech to `audio_path` (.mp3) and returns the word-level
    timing cues for that segment (timing starts at 0 for each segment).
    """
    return asyncio.run(_synthesize(text, audio_path))


def group_into_phrases(cues: List[Subtitle], words_per_caption: int = WORDS_PER_CAPTION) -> List[Subtitle]:
    """Combine word-level cues into short multi-word caption lines."""
    grouped = []
    for i in range(0, len(cues), words_per_caption):
        chunk = cues[i : i + words_per_caption]
        text = " ".join(c.content for c in chunk)
        grouped.append(Subtitle(index=0, start=chunk[0].start, end=chunk[-1].end, content=text))
    return grouped


def offset_cues(cues: List[Subtitle], offset_seconds: float) -> List[Subtitle]:
    """Shifts a segment's local cues forward by `offset_seconds`, so they
    land in the right place in the final, full-length video timeline."""
    offset = timedelta(seconds=offset_seconds)
    return [Subtitle(index=0, start=c.start + offset, end=c.end + offset, content=c.content) for c in cues]


def fill_gaps(cues: List[Subtitle], total_duration: float) -> List[Subtitle]:
    """
    Stretches every cue's end time forward to the start of the next cue (and
    the very first cue's start back to 0, and the last cue's end out to the
    end of the video). The result has zero gaps — a caption is on screen for
    every single moment of the video, instead of flicking off between
    phrases or at segment boundaries.
    """
    if not cues:
        return cues

    filled = []
    for i, cue in enumerate(cues):
        start = timedelta(seconds=0) if i == 0 else cue.start
        end = cues[i + 1].start if i + 1 < len(cues) else timedelta(seconds=total_duration)
        filled.append(Subtitle(index=0, start=start, end=end, content=cue.content))
    return filled


def write_srt(cues: List[Subtitle], srt_path: str) -> None:
    """Writes a final list of (already-offset) cues out as a real .srt file,
    re-numbering them in order."""
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(compose(cues, reindex=True, start_index=1))


def generate_voice_and_captions(text: str, audio_path: str, srt_path: str) -> None:
    """
    Convenience wrapper for testing this module on its own: writes audio AND
    a grouped .srt caption file for a single block of text in one call.
    """
    cues = synthesize_segment(text, audio_path)
    write_srt(group_into_phrases(cues), srt_path)


if __name__ == "__main__":
    # Quick manual test: python voice_gen.py
    generate_voice_and_captions(
        "This is a quick test of the voice and caption pipeline.",
        "test_voice.mp3",
        "test_voice.srt",
    )
    print("Wrote test_voice.mp3 and test_voice.srt")
