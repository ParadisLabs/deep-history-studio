"""
Deep History Studio — series configuration.
Every creative knob lives here. Change values freely; the engine reads them.
"""

# ---------------- identity ----------------
STUDIO_NAME = "Deep History Studio"
ENGINE_VERSION = "v1"
LANGUAGE = "Turkish"

# ---------------- voice (edge-tts) ----------------
# Chill documentary narrator. Swap freely:
#   en-US-GuyNeural        warm, conversational chill (default)
#   en-US-ChristopherNeural deep & steady (v1 voice)
#   en-GB-RyanNeural       British documentary vibe
VOICE = "tr-TR-AhmetNeural"
# Slightly slower than default reads as "chill"
# Optimal for Turkish engagement: slightly slower than default reads as "chill" but engaging
# Research suggests -15% to -10% for better comprehension and retention
VOICE_RATE = "-15%"
VOICE_PITCH = "-1Hz"

# ---------------- episode shape ----------------
# Target runtime in SECONDS (6-10 min episodes; one topic per episode)
TARGET_SECONDS_MIN = 360
TARGET_SECONDS_MAX = 600
# Words per second for this voice at the rate above (measured ~2.6 wps)
WORDS_PER_SECOND = 2.6
# Chapters per episode: intro, 3-5 body chapters, closer
MIN_CHAPTERS = 5
MAX_CHAPTERS = 7

# ---------------- visual style ----------------
# Consistent hand-drawn stick-figure documentary look, used by illustrator.py.
# Flux schnell accepts prompt + steps only, so keep exclusions out of unsupported fields.
STYLE_SUFFIX = ("hand-drawn stick-figure documentary illustration, expressive simple black line-art figures, consistent thin ink line weight, warm off-white textured paper background, restrained single muted ochre accent color, clear readable silhouettes, historically grounded props and architecture, editorial explainer illustration, flat 2D composition, vertical 9:16 framing, no text, no letters, no words, no watermark, not photorealistic")

# Retained as editorial guidance; the current Flux request schema has no negative_prompt field.
IMAGE_NEGATIVE = "text, letters, words, captions, watermark, realistic photo, photorealistic, color photograph"

# ---------------- captions ----------------
CAPTIONS = True
CAPTION_MAX_CHARS = 38          # wrap point for on-screen lines
CAPTION_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAPTION_FONTSIZE = 34

# ---------------- rendering ----------------
WIDTH, HEIGHT = 1080, 1920      # vertical 9:16 for TikTok/YouTube Shorts optimal engagement
FPS = 30
KEN_BURNS = True                # slow zoom/pan on every image
VIDEO_BITRATE = "900k"          # keeps 6-10 min under Telegram's 50MB
AUDIO_BITRATE = "96k"

# ---------------- writing model chain (Groq primary) ----------------
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    # qwen3-32b retired from standard Groq access 2026-07-17 -> removed
]
GROQ_MAX_COMPLETION_TOKENS = 12000  # headroom: gpt-oss reasoning + full script JSON
# gemini-flash-latest is an unstable alias; pin the stable GA flash model
GEMINI_MODEL = "gemini-3.8-flash"

# ---------------- research ----------------
# Wikipedia REST API is free, no key. These page fetches per topic cap the
# context size we hand the writer.
WIKI_MAX_PAGES = 4
WIKI_EXTRACT_CHARS = 6000

# ---------------- images ----------------
IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
IMAGE_STEPS = 4                  # schnell is 1-4 steps; 4 = best quality (max quality for flux)
IMAGES_PER_CHAPTER = 6           # ~30-42 images per episode (increased for better visual variety)

# ---------------- paths ----------------
STATE_PATH = "memory/state.json"
TOPICS_PATH = "memory/topics.json"
SOURCES_DIR = "memory/sources"
EPISODES_DIR = "episodes"

# ---------------- delivery ----------------
TELEGRAM_MB_LIMIT = 48           # send as file if under; artifact fallback above

# ---------------- OpsHub integration ----------------
HUB_EMIT = True                  # fire content.episode_ready on success
