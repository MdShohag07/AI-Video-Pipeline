---
title: Reelforge
emoji: 🎬
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Type a topic, get a captioned vertical video ready to upload.
---

# Reelforge — AI video pipeline

Type a topic and get a finished, captioned, vertical short. The script,
voiceover, scene images, background ambience, and final cut are all generated
automatically, then handed back as an upload-ready .mp4.

This Space runs a small Flask app (`app.py`) that drives the pipeline. API keys
are supplied as Space secrets, not committed to the repo.
