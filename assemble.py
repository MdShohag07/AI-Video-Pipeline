"""
Step 4: glue everything together — AI images (with a slow Ken Burns zoom),
their matching voice clips, optional background music, and burned-in
captions — into one finished, upload-ready vertical video.

This is the only step that doesn't call any AI model; it's just ffmpeg and
moviepy doing mechanical assembly, which is why it's the one part of this
pipeline fully tested ahead of time.
"""

import os
import subprocess
from typing import List

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    afx,
    concatenate_videoclips,
)
import imageio_ffmpeg

import config


def _build_scene_clip(image_path: str, audio_clip: AudioFileClip):
    """One scene = one AI image, slowly zoomed in (Ken Burns effect) for
    exactly as long as its matching voice line takes to say."""
    duration = audio_clip.duration

    base = ImageClip(image_path).with_duration(duration)
    # cover-fit the image to the output canvas first
    base = base.resized(height=config.OUTPUT_HEIGHT)
    if base.w < config.OUTPUT_WIDTH:
        base = base.resized(width=config.OUTPUT_WIDTH)

    zoomed = base.resized(lambda t: 1 + (config.ZOOM_FACTOR - 1) * (t / duration))
    positioned = zoomed.with_position("center")
    framed = CompositeVideoClip([positioned], size=(config.OUTPUT_WIDTH, config.OUTPUT_HEIGHT))

    return framed.with_audio(audio_clip)


def _mix_in_music(voice_audio, total_duration: float, music_path: str = None):
    """Layers background music under the voice track, looping or trimming it
    to fit, at a low volume. Tries `music_path` (the auto-fetched, topic
    matched track) first, falls back to the static config.MUSIC_PATH, and
    skips music entirely if neither exists — nothing breaks either way."""
    chosen_path = music_path or config.MUSIC_PATH
    if not chosen_path or not os.path.exists(chosen_path):
        return voice_audio

    music = AudioFileClip(chosen_path)
    if music.duration < total_duration:
        music = music.with_effects([afx.AudioLoop(duration=total_duration)])
    else:
        music = music.subclipped(0, total_duration)
    music = music.with_effects([afx.MultiplyVolume(config.MUSIC_VOLUME)])

    return CompositeAudioClip([voice_audio, music])


def _format_ass_time(td) -> str:
    total = max(td.total_seconds(), 0)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    seconds = total % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def _escape_ass_text(text: str) -> str:
    # { and } are override-tag delimiters in .ass — strip them so stray
    # characters in generated text can't be misread as formatting codes
    return text.replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def _write_ass_captions(cues, title_text: str, ass_path: str) -> None:
    """Builds an .ass subtitle file with two named styles: a bold, boxed
    TITLE cue (the hook + emoji) shown for the first few seconds, and bold,
    boxed CAPTION cues for the word-grouped narration throughout. ffmpeg
    burns this in directly — the styling lives in the file itself."""
    from datetime import timedelta

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {config.OUTPUT_WIDTH}\n"
        f"PlayResY: {config.OUTPUT_HEIGHT}\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Caption,{config.CAPTION_FONT},{config.CAPTION_FONTSIZE},&H00FFFFFF,"
        f"&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,1,2,60,60,"
        f"{config.CAPTION_MARGIN_V},1\n"
        f"Style: Title,{config.CAPTION_FONT},{config.TITLE_FONTSIZE},&H00FFFFFF,"
        f"&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,3,20,0,8,60,60,"
        f"{config.TITLE_MARGIN_V},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    lines = [header]

    if title_text:
        start = _format_ass_time(timedelta(seconds=0))
        end = _format_ass_time(timedelta(seconds=config.TITLE_DURATION))
        lines.append(f"Dialogue: 0,{start},{end},Title,,0,0,0,,{_escape_ass_text(title_text)}\n")

    for cue in cues:
        start = _format_ass_time(cue.start)
        end = _format_ass_time(cue.end)
        text = _escape_ass_text(cue.content)
        if text:
            lines.append(f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{text}\n")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _burn_captions(input_video_path: str, ass_path: str, output_video_path: str) -> None:
    """Hard-burns the .ass captions into the video using ffmpeg's subtitles
    filter — more reliable than moviepy's text rendering and needs no extra
    ImageMagick setup."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # ffmpeg's subtitles filter treats ':' and '\' specially in its own
    # argument string, so the path needs escaping — this matters most on
    # Windows where paths contain both backslashes and a drive-letter colon.
    safe_ass_path = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{safe_ass_path}'"

    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_video_path,
        "-vf", vf,
        "-c:a", "copy",
        output_video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg caption burn-in failed:\n{result.stderr[-2000:]}")


def assemble_video(
    image_paths: List[str],
    audio_paths: List[str],
    caption_cues: list,
    final_output_path: str,
    title_text: str = "",
    workdir: str = None,
    music_path: str = None,
) -> str:
    """
    Builds the finished video from per-scene images + per-scene audio, mixes
    in background music if available, and burns in a boxed title hook plus
    synced bottom captions.

    `image_paths` and `audio_paths` must be the same length and in the same
    scene order. `caption_cues` is the list of (already time-offset) word-
    group Subtitle objects for the whole video — see main.py. `title_text`
    is the short emoji+hook line shown for the first few seconds.
    `music_path`, if given, is the auto-fetched topic-matched track; falls
    back to config.MUSIC_PATH, then to no music at all.

    Returns the path to the final captioned video.
    """
    assert len(image_paths) == len(audio_paths), "Need exactly one image per audio segment"

    workdir = workdir or config.WORKDIR
    os.makedirs(workdir, exist_ok=True)

    audio_clips = [AudioFileClip(p) for p in audio_paths]
    scene_clips = [_build_scene_clip(img, aud) for img, aud in zip(image_paths, audio_clips)]

    video = concatenate_videoclips(scene_clips, method="compose")
    total_duration = video.duration

    mixed_audio = _mix_in_music(video.audio, total_duration, music_path)
    video = video.with_audio(mixed_audio)

    silent_path = os.path.join(workdir, "_assembled_no_captions.mp4")
    video.write_videofile(
        silent_path,
        fps=config.FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    os.makedirs(os.path.dirname(final_output_path) or ".", exist_ok=True)
    ass_path = os.path.join(workdir, "captions.ass")
    _write_ass_captions(caption_cues, title_text, ass_path)
    _burn_captions(silent_path, ass_path, final_output_path)

    return final_output_path
