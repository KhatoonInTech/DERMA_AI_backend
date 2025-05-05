# Agents/UserIntakeAgent.py

from Initialization import send_message_to_llm, transcribe_audio_vertex, model
from vertexai.generative_models import ChatSession # Import ChatSession if needed here


def describe_visuals(image_bytes: bytes, mime_type: str) -> str:
    """
    Analyzes an image using the multimodal capabilities of Gemini.
    Starts a *temporary* chat session for this single request.
    """
    # For single-turn visual description, we can create a temporary chat
    # If this needs to be part of a larger conversation, pass the main chat session
    temp_chat = model.start_chat(history=[])

    prompt = (
        "Analyze the image provided as a board-certified dermatologist. "
        "1) List **all** observable skin features under these headings: Color, Morphology, Surface Changes, Texture, Distribution, Hair/Nails, Secondary Signs.  "
        "2) Highlight any subtle or atypical findings.  "
        "3) Be purely descriptive—no diagnosis or assumptions.  "
        "Format your answer as a Markdown bullet list."
    )
    visual_response = send_message_to_llm(
        temp_chat, # Use the temporary chat
        prompt,
        image_bytes=image_bytes,
        image_mime_type=mime_type
    )
    # Check if the response indicates an error
    if isinstance(visual_response, str) and visual_response.startswith("Error:"):
        print(f"❌ Error getting visual description: {visual_response}")
        return visual_response # Propagate error message
    elif not isinstance(visual_response, str):
         print(f"❌ Unexpected response type for visual description: {type(visual_response)}")
         return "Error: Unexpected response type from LLM during visual description."

    print("Visual description generated.")
    return visual_response

