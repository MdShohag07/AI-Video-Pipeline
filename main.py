"""
Run the full pipeline: one topic in -> one finished, upload-ready vertical
video out. Every generation step is free; only your own electricity and
time cost anything.

Usage:
    python main.py "3 AI tools that actually save you time"

The finished video is written to output/<slugified-topic>.mp4
"""

import os
import re
import sys

import config
import script_gen
import voice_gen
import image_gen
import music_gen
import assemble


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "video"


def run_pipeline(topic: str) -> str:
    workdir = os.path.join(config.WORKDIR, _slugify(topic))
    os.makedirs(workdir, exist_ok=True)

    print(f"[1/5] Writing the script for: {topic!r}")
    try:
        script = script_gen.generate_script(topic)
    except Exception as e:
        raise RuntimeError(
            "Script generation failed. This step calls pollinations.ai's free "
            "text model over the internet — check your connection, or try "
            f"again in a minute (the free model can be briefly overloaded). Original error: {e}"
        ) from e

    segments = script["segments"]
    print(f"      -> got {len(segments)} segments")

    print("[2/5] Generating voice + captions for each segment")
    audio_paths = []
    all_caption_cues = []
    cumulative_seconds = 0.0

    for i, seg in enumerate(segments):
        audio_path = os.path.join(workdir, f"audio_{i}.mp3")
        try:
            cues = voice_gen.synthesize_segment(seg["narration"], audio_path)
        except Exception as e:
            raise RuntimeError(
                "Voice generation failed. This step calls Microsoft's free "
                "edge-tts service — check your connection, or try a "
                f"different VOICE in config.py if this keeps happening. Original error: {e}"
            ) from e

        from moviepy import AudioFileClip
        segment_duration = AudioFileClip(audio_path).duration

        phrases = voice_gen.group_into_phrases(cues)
        all_caption_cues.extend(voice_gen.offset_cues(phrases, cumulative_seconds))

        cumulative_seconds += segment_duration
        audio_paths.append(audio_path)
        print(f"      -> segment {i + 1}/{len(segments)} voiced ({segment_duration:.1f}s)")

    all_caption_cues = voice_gen.fill_gaps(all_caption_cues, cumulative_seconds)
    title_text = script.get("title", "")

    print("[3/5] Finding matching stock images for each scene")
    image_prompts = [seg["image_prompt"] for seg in segments]
    try:
        image_paths = image_gen.generate_images(image_prompts, workdir)
    except Exception as e:
        raise RuntimeError(
            "Image generation failed. This step calls Pexels' free stock photo "
            "API — check your connection and that PEXELS_API_KEY is set in your "
            f".env file. Original error: {e}"
        ) from e

    print("[4/5] Looking for a matching background ambience track (optional)")
    mood = script.get("background_mood", "none")
    music_path = music_gen.find_background_track(mood, os.path.join(workdir, "background.mp3"))

    print("[5/5] Assembling the final video (this is the slow step)")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    final_path = os.path.join(config.OUTPUT_DIR, f"{_slugify(topic)}.mp4")
    assemble.assemble_video(
        image_paths,
        audio_paths,
        all_caption_cues,
        final_path,
        title_text=title_text,
        workdir=workdir,
        music_path=music_path,
    )

    print(f"\nDone. Upload-ready video: {final_path}")
    return final_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "your topic here"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    run_pipeline(topic)
