# Initialization.py
import vertexai
import json
import re
import io
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part, Content, ChatSession
import speech_recognition as sr
from pydub import AudioSegment

# Import configuration variables
from CONFIGURATION import (
    VERTEX_PROJECT_ID,
    VERTEX_LOCATION,
    MODEL_NAME,
    TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    SAFETY_SETTINGS,
    AUDIO_FORMAT_MAP
)

# --- Initialize Vertex AI ---
print("Initializing Vertex AI...")
try:
    vertexai.init(project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)
    print("Vertex AI Initialized Successfully.")
except Exception as e:
    print(f"❌ Error initializing Vertex AI: {e}")
    raise

# --- Load Generative Model ---
print(f"Loading Generative Model: {MODEL_NAME}")
try:
    model = GenerativeModel(
        MODEL_NAME,
        system_instruction=[
            "You are a highly experienced, board-certified dermatologist.",
            "Always think step-by-step, reference clinical reasoning, and answer strictly in JSON if asked.",
            "When diagnosing, cite visual features, propose differentials, and state confidence levels.",
            "IMPORTANT: NEVER provide medical advice or diagnosis for real-world cases. Always state that this is for informational purposes only and the user should consult a qualified healthcare professional.",
            "Disclaimers about not being a real doctor should be included where appropriate, especially in final summaries or reports."
        ]
    )
    print("Generative Model Loaded Successfully.")
except Exception as e:
    print(f"❌ Error loading Generative Model: {e}")
    raise


# --- Initialize Speech Recognizer ---
# Keep the recognizer instance ready
recognizer = sr.Recognizer()

# --- Generation Config ---
generation_config = GenerationConfig(
    temperature=TEMPERATURE,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    top_p=0.9,
    top_k=40
)

# --- Helper Functions ---
def parse_json_response(response_text: str):
    """Attempts to parse a JSON object or array from the LLM response text."""
    response_raw = response_text.strip()
    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    response_raw = re.sub(r'^```(?:json)?\s*|```\s*$', '', response_raw, flags=re.MULTILINE).strip()

    # Try to find a JSON object '{...}' or array '[...]'
    match = re.search(r'(\{.*\}|\[.*\])', response_raw, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decoding failed after extracting potential JSON: {e}")
            print(f"--- Extracted String: ---\n{json_str}\n------------------------")
            # Fallback: If extraction fails, try parsing the whole cleaned response
            try:
                print("--- Attempting to parse the whole cleaned response ---")
                return json.loads(response_raw)
            except json.JSONDecodeError as final_e:
                print(f"❌ Final JSON decoding failed: {final_e}")
                print(f"--- Raw Response Text: ---\n{response_text}\n--------------------------")
                # Return the raw text as a last resort, indicating failure
                return {"error": "Failed to parse JSON response", "raw_response": response_text}
    else:
        # If no JSON object/array found, return the raw text, maybe it's not JSON
        print("⚠️ No JSON object or array found in the response.")
        # Return the raw text or a structured error
        return {"warning": "Response does not appear to contain JSON", "raw_response": response_text}


def send_message_to_llm(chat_session:ChatSession, prompt: str, image_bytes: bytes = None, image_mime_type: str = None):
    """Sends a prompt (and optionally an image) to the Vertex AI Gemini model using a provided chat session."""
    try:
        contents = [prompt]
        if image_bytes and image_mime_type:
            image_part = Part.from_data(image_bytes, mime_type=image_mime_type)
            contents.append(image_part)

        # print(f"\n--- Sending to LLM ---\nPrompt: {prompt}\nImage: {'Yes' if image_bytes else 'No'}\n-----------------------\n")

        response = chat_session.send_message(
            contents,
            generation_config=generation_config,
            safety_settings=SAFETY_SETTINGS,
            stream=False # Ensure full response is received
        )

        # print(f"\n--- Received from LLM ---\n{response.text}\n-------------------------\n")
        # Accessing candidates and content directly
        # print(response.candidates[0].content.parts[0].text)

        # Handle potential lack of text part (e.g., if blocked)
        if response.candidates and response.candidates[0].content.parts:
             return response.candidates[0].content.parts[0].text
        else:
             # Log the full response for debugging if text is missing
             print(f"⚠️ LLM response missing expected text part. Full response: {response}")
             # Check for finish reason (e.g., safety)
             finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
             safety_ratings = response.candidates[0].safety_ratings if response.candidates else []
             return f"Error: LLM response generation failed or was blocked. Reason: {finish_reason}. Safety: {safety_ratings}"


    except Exception as e:
        print(f"❌ Error interacting with LLM: {e}")
        print(f"Chat History at error: {chat_session.history}")
        # Return a structured error instead of raising to allow API to respond
        return f"Error: Exception during LLM interaction - {e}"


def transcribe_audio_vertex(audio_bytes: bytes, mime_type: str) -> str:
    """
    Transcribes audio from bytes using speech_recognition library.
    Converts various audio formats to WAV in memory using pydub.
    """
    file_format = AUDIO_FORMAT_MAP.get(mime_type)
    if not file_format:
        print(f"Unsupported audio MIME type for transcription: {mime_type}")
        return "Error: Unsupported audio format for transcription."

    try:
        # Load audio from byte string using pydub
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=file_format)

        # Export to WAV in memory
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)  # Reset to the beginning

        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source) # Use the initialized recognizer

        try:
            text = recognizer.recognize_google(audio_data)
            print(f"Transcription successful.")
            return text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return "Error: Could not understand audio."
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return f"Error: Speech Recognition service unavailable - {e}"

    except Exception as e: # Catching pydub or other errors
        print(f"Error during audio processing or transcription: {e}")
        return f"Error: Failed to process audio - {e}"