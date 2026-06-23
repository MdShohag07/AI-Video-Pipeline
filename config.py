"""
Central settings for the AI video pipeline.
Change things here — you shouldn't need to touch the other files.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if one exists, without erroring if it doesn't

# ---------------------------------------------------------------------------
# Pollinations.ai API key (optional, but recommended)
# ---------------------------------------------------------------------------
# pollinations.ai's no-signup tier is rate-limited and can demand a key once
# you've made a few requests. Get a free key from your pollinations.ai
# account dashboard, then create a file named ".env" in this same folder
# (next to config.py) containing exactly one line:
#   POLLINATIONS_API_KEY=your_key_here
# Never put the key directly in this file — .env keeps it out of any code
# you might later share, back up, or put on GitHub.
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY")

# ---------------------------------------------------------------------------
# Script generation (pollinations.ai text model — free, no API key)
# ---------------------------------------------------------------------------
# Pollinations consolidated their old separate subdomains (text.pollinations.ai,
# image.pollinations.ai) into one unified host. If this ever 404s again,
# check https://pollinations.ai or their GitHub for the current path.
POLLINATIONS_TEXT_URL = "https://gen.pollinations.ai/text"
TEXT_MODEL = "mistral"        # smaller open-weight models like this are usually still
                               # free on pollinations, unlike the big GPT/Claude/Gemini
                               # ones. If this still costs Pollen, check
                               # https://gen.pollinations.ai/text/models in your browser
                               # for whichever model is currently marked free/$0.
NUM_SCENES = 5                # how many image scenes the script gets split into

# ---------------------------------------------------------------------------
# Voice + captions (edge-tts — free, no API key, runs locally)
# ---------------------------------------------------------------------------
# Run `edge-tts --list-voices` in your terminal to see every option.
# A few useful ones for Bangladesh / India content:
#   "bn-BD-NabanitaNeural"   -> Bangla, female
#   "bn-BD-PradeepNeural"    -> Bangla, male
#   "hi-IN-SwaraNeural"      -> Hindi, female
#   "hi-IN-MadhurNeural"     -> Hindi, male
#   "en-IN-NeerjaNeural"     -> English, Indian accent, female
VOICE = "en-IN-NeerjaNeural"
SPEECH_RATE = "+0%"           # e.g. "+10%" to speak a bit faster

# ---------------------------------------------------------------------------
# Scene images (Pexels — genuinely free stock photos, no metered credits)
# ---------------------------------------------------------------------------
# After discovering pollinations.ai's free image tier is too rate-limited for
# real use, we switched to Pexels — a stock photo library that's been
# reliably free for years, not a metered AI-generation service.
# Get a free key (no payment info needed) at https://www.pexels.com/api/
# then add it to your .env file as:
#   PEXELS_API_KEY=your_key_here
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# ---------------------------------------------------------------------------
# Final video
# ---------------------------------------------------------------------------
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 30
ZOOM_FACTOR = 1.15            # how much each image zooms in over its scene (Ken Burns effect)

# ---------------------------------------------------------------------------
# Captions + title (burned in with ffmpeg, .ass styling — bold text on a
# semi-transparent box, a top title hook + synced bottom captions)
# ---------------------------------------------------------------------------
CAPTION_FONT = "Arial"        # guaranteed to exist on Windows; change if you prefer another
CAPTION_FONTSIZE = 72          # sized for a 1080x1920 canvas — was 14, which rendered
                               # nearly invisible once explicit PlayRes was added below
CAPTION_MARGIN_V = 140        # bottom captions' distance from the bottom of the frame, in px
TITLE_FONTSIZE = 88
TITLE_MARGIN_V = 160          # title's distance from the TOP of the frame, in px
TITLE_DURATION = 3.0          # how many seconds the title hook stays on screen

# ---------------------------------------------------------------------------
# Background ambience (Freesound — free, long-established sound library,
# used to auto-pick a track matching the video's topic, e.g. soft rain
# sounds for a video about rain)
# ---------------------------------------------------------------------------
# Optional: get a free key at https://freesound.org/apiv2/apply/ then add it
# to your .env file as FREESOUND_API_KEY=your_key_here. If you skip this,
# videos are just made with no background sound — nothing breaks.
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY")
FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/text/"
MUSIC_VOLUME = 0.12            # how loud the background track sits under the voice

# Manual fallback: if you'd rather pick your own fixed track instead of the
# automatic per-video one, drop an mp3 here and it's used whenever the
# automatic Freesound lookup doesn't find or fetch anything.
MUSIC_PATH = "assets/background_music.mp3"

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
WORKDIR = "workdir"
OUTPUT_DIR = "output"
