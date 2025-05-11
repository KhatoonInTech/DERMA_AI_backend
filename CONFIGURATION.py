# CONFIGURATION.py
import os
from dotenv import load_dotenv
from vertexai.generative_models import HarmCategory, HarmBlockThreshold

# Load environment variables from .env file
load_dotenv(override=True)  # Force reload of environment variables

# --- Model Configuration ---
MODEL_NAME = "gemini-2.0-flash-001"  # Updated to a generally available model
TEMPERATURE = 0.1  # Lower temperature for more deterministic medical responses
MAX_OUTPUT_TOKENS = 8192  # Adjust as needed, Flash has 8192 context
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# --- API Keys & Project Info (Loaded from Environment Variables) ---
# Ensure these are set in your .env file or environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')
IMAGE_ENGINE_ID = os.getenv('IMAGE_ENGINE_ID')
VERTEX_PROJECT_ID = os.getenv('VERTEX_PROJECT_ID')
VERTEX_LOCATION = os.getenv('VERTEX_LOCATION')

# --- Input Validation ---
if not all([GOOGLE_API_KEY, SEARCH_ENGINE_ID, IMAGE_ENGINE_ID, VERTEX_PROJECT_ID, VERTEX_LOCATION]):
    raise ValueError(
        "One or more required environment variables are missing. "
        "Please set GOOGLE_API_KEY, SEARCH_ENGINE_ID, IMAGE_ENGINE_ID, "
        "VERTEX_PROJECT_ID, and VERTEX_LOCATION in your .env file or environment."
    )

# Explicitly set the project ID for libraries relying on env vars if needed
# os.environ['GOOGLE_CLOUD_PROJECT'] = VERTEX_PROJECT_ID # Often handled by vertexai.init

# --- Other Constants ---
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
SUPPORTED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac", "audio/ogg", "audio/webm"}
AUDIO_FORMAT_MAP = { # Map MIME type to pydub format string
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
    "audio/ogg": "ogg",
    "audio/webm": "webm", # pydub might need ffmpeg for webm
}
