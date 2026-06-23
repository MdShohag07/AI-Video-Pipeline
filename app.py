"""
Web front-end for the AI video pipeline.

Run it from the project root (the same folder as main.py):

    pip install flask
    python app.py

then open http://127.0.0.1:5000 in your browser, type a topic, and watch
the pipeline build the video live. When it finishes, the video plays in the
page and the Download button saves the .mp4.

This file doesn't generate anything itself — it just calls the same
script_gen / voice_gen / image_gen / music_gen / assemble steps that main.py
uses, reporting progress to the page after each step so you can see where it
is. Each topic runs in a background thread; the page polls /status to follow
along.
"""

import os
import re
import threading
import uuid

from flask import Flask, Response, jsonify, render_template, request, send_file, abort

import config
import script_gen
import voice_gen
import image_gen
import music_gen
import assemble

app = Flask(__name__)

# In-memory job store. Fine for local single-user use; if you ever deploy this
# for multiple people at once you'd swap this for something persistent.
JOBS = {}
LOCK = threading.Lock()

# Human-readable name for each pipeline stage, in order. The front-end shows
# this exact list and lights up the active one.
STAGES = [
    "Writing the script",
    "Recording the voiceover",
    "Finding scene images",
    "Adding background ambience",
    "Assembling the video",
]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "video"


def _update(job_id: str, **fields) -> None:
    with LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(fields)


def _run_job(topic: str, job_id: str) -> None:
    """Runs the full pipeline for one topic, updating the job's progress after
    each stage. Mirrors main.run_pipeline, with progress reporting added."""
    try:
        workdir = os.path.join(config.WORKDIR, _slugify(topic))
        os.makedirs(workdir, exist_ok=True)

        # ---- Stage 1: script -------------------------------------------------
        _update(job_id, status="running", step=1, label=STAGES[0], detail="")
        script = script_gen.generate_script(topic)
        segments = script["segments"]
        _update(job_id, detail=f"{len(segments)} segments")

        # ---- Stage 2: voice + captions --------------------------------------
        _update(job_id, step=2, label=STAGES[1], detail="")
        from moviepy import AudioFileClip

        audio_paths = []
        all_caption_cues = []
        cumulative_seconds = 0.0
        for i, seg in enumerate(segments):
            audio_path = os.path.join(workdir, f"audio_{i}.mp3")
            cues = voice_gen.synthesize_segment(seg["narration"], audio_path)
            segment_duration = AudioFileClip(audio_path).duration

            phrases = voice_gen.group_into_phrases(cues)
            all_caption_cues.extend(voice_gen.offset_cues(phrases, cumulative_seconds))
            cumulative_seconds += segment_duration
            audio_paths.append(audio_path)
            _update(job_id, detail=f"segment {i + 1}/{len(segments)} voiced")

        all_caption_cues = voice_gen.fill_gaps(all_caption_cues, cumulative_seconds)
        title_text = script.get("title", "")

        # ---- Stage 3: images -------------------------------------------------
        _update(job_id, step=3, label=STAGES[2], detail="")
        image_prompts = [seg["image_prompt"] for seg in segments]
        image_paths = image_gen.generate_images(image_prompts, workdir)

        # ---- Stage 4: background ambience (optional) ------------------------
        _update(job_id, step=4, label=STAGES[3], detail="")
        mood = script.get("background_mood", "none")
        music_path = music_gen.find_background_track(
            mood, os.path.join(workdir, "background.mp3")
        )

        # ---- Stage 5: assemble ----------------------------------------------
        _update(job_id, step=5, label=STAGES[4], detail="this is the slow step")
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        slug = _slugify(topic)
        final_path = os.path.join(config.OUTPUT_DIR, f"{slug}.mp4")
        assemble.assemble_video(
            image_paths,
            audio_paths,
            all_caption_cues,
            final_path,
            title_text=title_text,
            workdir=workdir,
            music_path=music_path,
        )

        with LOCK:
            JOBS[job_id].update(
                status="done",
                step=len(STAGES) + 1,
                label="Done",
                detail="",
                final_path=final_path,
                filename=f"{slug}.mp4",
                video_url=f"/media/{job_id}",
            )

    except Exception as e:  # surface a readable reason to the page
        _update(job_id, status="error", error=str(e) or e.__class__.__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True, silent=True) or {}
    topic = (data.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Type a topic first."}), 400

    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "step": 0,
            "label": "Starting",
            "detail": "",
            "topic": topic,
            "stages": STAGES,
        }
    threading.Thread(target=_run_job, args=(topic, job_id), daemon=True).start()
    return jsonify({"job_id": job_id, "stages": STAGES})


@app.route("/status/<job_id>")
def status(job_id):
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Unknown job."}), 404
        public = {
            k: v for k, v in job.items() if k != "final_path"
        }
    return jsonify(public)


@app.route("/media/<job_id>")
def media(job_id):
    with LOCK:
        job = JOBS.get(job_id)
        final_path = job.get("final_path") if job else None
        filename = job.get("filename", "video.mp4") if job else "video.mp4"
    if not final_path or not os.path.exists(final_path):
        abort(404)
    as_attachment = request.args.get("download") == "1"
    return send_file(
        final_path,
        mimetype="video/mp4",
        as_attachment=as_attachment,
        download_name=filename,
        conditional=True,  # lets the <video> tag seek/scrub
    )


if __name__ == "__main__":
    # threaded=True so progress polls and video streaming aren't blocked while
    # a generation thread is running.
    #
    # host 0.0.0.0 makes it reachable inside a hosting container; PORT is read
    # from the environment so platforms (Hugging Face Spaces, Render, etc.) can
    # tell the app which port to listen on. Locally, with no PORT set, it falls
    # back to 5000 — so `python app.py` still opens at http://127.0.0.1:5000.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
