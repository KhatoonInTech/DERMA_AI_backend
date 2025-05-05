import io
import mimetypes
from typing import Optional

# --- Text Extraction Libraries ---
# Image OCR
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    print("⚠️ Warning: pytesseract or Pillow not found. OCR for images will not be available.")
    print("   Install them: pip install pytesseract Pillow")
    print("   AND ensure Tesseract OCR engine is installed on your system.")

# PDF Reading
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("⚠️ Warning: PyPDF2 not found. PDF text extraction will not be available.")
    print("   Install it: pip install PyPDF2")

# Word Document Reading (.docx)
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ Warning: python-docx not found. Word (.docx) text extraction will not be available.")
    print("   Install it: pip install python-docx")


# --- LLM Interaction ---
from Initialization import model, send_message_to_llm

# --- Constants ---
# Define supported MIME types based on available libraries
SUPPORTED_MIME_TYPES = {
    "application/pdf": PYPDF2_AVAILABLE,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCX_AVAILABLE, # .docx
    # Add common image types if pytesseract is available
    "image/png": PYTESSERACT_AVAILABLE,
    "image/jpeg": PYTESSERACT_AVAILABLE,
    "image/tiff": PYTESSERACT_AVAILABLE,
    "image/bmp": PYTESSERACT_AVAILABLE,
}

# Maximum characters to send to LLM to avoid context window issues
MAX_TEXT_LENGTH = 25000

def extract_text_from_bytes(file_bytes: bytes, mime_type: str) -> Optional[str]:
    """
    Extracts text content from file bytes based on the MIME type.

    Args:
        file_bytes: The content of the file as bytes.
        mime_type: The MIME type of the file (e.g., 'application/pdf').

    Returns:
        The extracted text as a string, or None if extraction fails or type is unsupported.
    """
    print(f"Attempting text extraction for MIME type: {mime_type}")

    # Check if type is supported and library is available
    if not SUPPORTED_MIME_TYPES.get(mime_type):
        if mime_type in SUPPORTED_MIME_TYPES: # Key exists but value is False
             print(f"❌ Extraction skipped: Library for {mime_type} is not installed.")
        else:
            print(f"❌ Extraction skipped: MIME type {mime_type} is not supported by this function.")
        return None

    extracted_text = ""

    try:
        # --- PDF Handling ---
        if mime_type == "application/pdf":
            pdf_file = io.BytesIO(file_bytes)
            reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(reader.pages)
            print(f"  Processing PDF with {num_pages} pages...")
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"
                    # else:
                    #     print(f"    No text found on page {i+1}") # Optional logging
                except Exception as page_e:
                     print(f"  ⚠️ Error extracting text from PDF page {i+1}: {page_e}")
            print(f"  Finished PDF processing.")

        # --- Word (.docx) Handling ---
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc_file = io.BytesIO(file_bytes)
            document = docx.Document(doc_file)
            print("  Processing DOCX file...")
            for para in document.paragraphs:
                if para.text:
                     extracted_text += para.text + "\n"
            # Consider adding table extraction if needed (more complex)
            print("  Finished DOCX processing.")

        # --- Image OCR Handling ---
        elif mime_type.startswith("image/"):
            print("  Processing image file with OCR (Tesseract)...")
            try:
                img = Image.open(io.BytesIO(file_bytes))
                # You might need preprocessing here for better OCR results (e.g., grayscale, thresholding)
                extracted_text = pytesseract.image_to_string(img)
                print("  Finished OCR processing.")
            except pytesseract.TesseractNotFoundError:
                print("❌ OCR Error: Tesseract executable not found in your PATH.")
                print("   Please install Tesseract OCR engine: https://github.com/tesseract-ocr/tesseract#installing-tesseract")
                return None
            except Exception as ocr_e:
                 print(f"❌ An error occurred during OCR: {ocr_e}")
                 return None

    except Exception as e:
        print(f"❌ An unexpected error occurred during text extraction for {mime_type}: {e}")
        import traceback
        traceback.print_exc() # Log full traceback for debugging
        return None

    cleaned_text = extracted_text.strip()
    if not cleaned_text:
         print("⚠️ No text could be extracted from the file.")
         return None

    print(f"✅ Text extracted successfully ({len(cleaned_text)} characters).")
    return cleaned_text


def analyze_report_file(file_bytes: bytes, mime_type: str) -> str:
    """
    Analyzes a report file (Image, PDF, DOCX) by extracting text, sending it to
    an LLM, and asking for a simple explanation.

    Args:
        file_bytes: The byte content of the report file.
        mime_type: The MIME type of the file.

    Returns:
        A string containing the LLM's analysis/summary in simple terms,
        or an error message if processing fails.
    """
    print(f"\n--- Starting Report Analysis for type: {mime_type} ---")

    # 1. Extract Text
    extracted_text = extract_text_from_bytes(file_bytes, mime_type)

    if not extracted_text:
        return "Error: Could not extract text from the provided file or the file type is not supported/library missing."

    # 2. Check Text Length and Truncate if Necessary
    if len(extracted_text) > MAX_TEXT_LENGTH:
        print(f"⚠️ Extracted text ({len(extracted_text)} chars) exceeds maximum length ({MAX_TEXT_LENGTH}). Truncating.")
        extracted_text = extracted_text[:MAX_TEXT_LENGTH] + "\n... [Content Truncated]"

    # 3. Prepare Prompt for LLM
    prompt = f"""
    Here is the text extracted from a medical report:
    --- START OF REPORT TEXT ---
    {extracted_text}
    --- END OF REPORT TEXT ---

    Please analyze this medical report thoroughly and explain it in simple, easy-to-understand language for a layperson (someone without a medical background).

    Your explanation should cover:
    1.  **Main Findings:** What are the key results or observations mentioned?
    2.  **Medical Terminology:** Define any complex medical terms used in the report in plain English.
    3.  **Overall Meaning:** What is the general conclusion or significance of the report?
    4.  **Actionable Information (if any):** Does the report suggest any next steps or recommendations (without giving direct medical advice)?

    Structure your response clearly. Avoid overly technical jargon in your explanation. Ensure the tone is informative and helpful.
    """

    # 4. Send to LLM using a temporary chat session
    print("Sending extracted text to LLM for analysis...")
    try:
        # Create a temporary chat session for this single analysis task
        temp_chat_session = model.start_chat(history=[])
        llm_response = send_message_to_llm(temp_chat_session, prompt)

        # send_message_to_llm already handles basic error string formatting
        if isinstance(llm_response, str) and llm_response.startswith("Error:"):
            print(f"❌ LLM analysis failed: {llm_response}")
            return llm_response # Return the specific error from the LLM function
        elif not isinstance(llm_response, str) or not llm_response.strip():
             print("❌ LLM returned an empty or invalid response.")
             return "Error: Received an empty or invalid response from the analysis model."
        else:
            print("✅ LLM analysis successful.")
            return llm_response.strip() # Return the successful analysis string

    except Exception as e:
        print(f"❌ An unexpected error occurred while communicating with the LLM: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: An unexpected error occurred during LLM communication: {e}"