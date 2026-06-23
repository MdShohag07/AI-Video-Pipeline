# Container for deploying the AI video pipeline web app on Hugging Face Spaces
# (free CPU tier: 2 vCPU, 16 GB RAM). Builds the same app you run locally.

FROM python:3.12-slim

# System fonts so the burned-in captions actually render. libass (used by the
# caption step) needs a real font on disk; fonts-liberation also registers an
# "Arial" alias via fontconfig, so config.py's CAPTION_FONT="Arial" resolves.
# fonts-dejavu-core is a safe fallback if you switch CAPTION_FONT to "DejaVu Sans".
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-liberation \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs your container as uid 1000 — create a matching user
# so file writes (workdir/, output/) don't hit permission errors.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860

WORKDIR /home/user/app

# Install Python deps first (better build caching)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-fetch the ffmpeg binary that imageio-ffmpeg uses, so the first video
# render doesn't pause to download it at runtime.
RUN python -c "import imageio_ffmpeg; imageio_ffmpeg.get_ffmpeg_exe()"

# Copy the rest of the project (app.py, config.py, the pipeline modules,
# templates/). Your .env is gitignored and must NOT be here — set the keys as
# Space secrets instead (see the deploy steps).
COPY --chown=user . .

EXPOSE 7860
CMD ["python", "app.py"]
