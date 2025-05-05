# app.py
import os
import io
import time
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

import mimetypes

# Import configurations and initializations
import CONFIGURATION as cfg
# --- Import only necessary items from Initialization ---
from Initialization import model, send_message_to_llm, parse_json_response
from Initialization import transcribe_audio_vertex, ChatSession # Import ChatSession here

# Import Agent functions
from Agents.UserIntakeAgent import describe_visuals
from Agents.DiagnosisAgent import (
    extract_symptoms,
    generate_diagnosis_questions,
    get_initial_diagnosis,
    perform_deep_research,
    get_final_diagnosis
)
from Agents.ReportingGenerationAgent import generate_report_markdown, generate_pdf_from_md
from Agents.ReportingAnalysisAgent import analyze_report_file
# --- Import the new Chatbot Agent function ---
from Agents.chatbot import generate_chat_response


# --- FastAPI App Initialization ---
# ... (app initialization remains the same) ...
app = FastAPI(
    title="DermaAI API",
    description="Simulated dermatology assistant with assessment, report analysis, and conversation capabilities.",
    version="1.1.0",
)

# --- In-Memory State Management ---
# ... (conversation_histories remains the same - still not for production) ...
conversation_histories: Dict[str, ChatSession] = {}

# --- Pydantic Models ---
# ... (Pydantic models remain the same) ...
class QuestionRequest(BaseModel):
    statement: str = Field(..., description="Initial user statement about their concern.", example="I have an itchy red rash on my arm.")
    symptoms: Optional[List[str]] = Field(None, description="Optional pre-extracted list of symptoms.", example=["RASH", "ITCHING", "REDNESS"])

class QuestionResponse(BaseModel):
    message: str
    processing_time_seconds: float
    questions: List[str]
    statement_processed: str
    symptoms_used: List[str]

class AssessmentResponse(BaseModel):
    message: str
    processing_time_seconds: float
    final_assessment: Dict[str, Any]
    report_markdown: str
    initial_diagnosis: Optional[Dict[str, Any]] = None
    extracted_symptoms: Optional[List[str]] = None
    visual_description_if_any: Optional[str] = None

class ReportAnalysisResponse(BaseModel):
    message: str
    processing_time_seconds: float
    analysis_summary: str
    file_processed: str
    mime_type: str

class ConversationRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Existing session ID to continue a conversation. If None, a new session starts.")
    query: str = Field(..., description="The user's latest message or question.")

class ConversationResponse(BaseModel):
    session_id: str
    response: str
    processing_time_seconds: float

class PdfRequest(BaseModel):
    final_assessment: Dict[str, Any] = Field(..., description="The final_assessment object from the /assess endpoint.")
    visual_description: Optional[str] = Field(None, description="Optional visual description if an image was processed.")
    report_markdown: Optional[str] = Field(None, description="Optional pre-generated markdown report.")


# --- Helper Function for Input Processing ---
# ... (process_input remains the same) ...
async def process_input(text_input: Optional[str], file_input: Optional[UploadFile]) -> tuple[str, Optional[str], Optional[bytes], Optional[str]]:
    """Processes text or file input, returning initial statement, visual description, content, mime type."""
    initial_statement = ""
    visual_description = None
    file_content = None
    mime_type = None

    if file_input:
        file_content = await file_input.read()
        mime_type = file_input.content_type
        if not mime_type or mime_type == 'application/octet-stream':
             mime_type, _ = mimetypes.guess_type(file_input.filename)
             print(f"Guessed MIME type as: {mime_type} for file {file_input.filename}")

        if not mime_type:
             await file_input.close()
             raise HTTPException(status_code=415, detail=f"Could not determine MIME type for file: {file_input.filename}")

        print(f"Processing uploaded file: {file_input.filename}, Type: {mime_type}")

        if mime_type in cfg.SUPPORTED_IMAGE_TYPES:
            print("Input is an image. Generating visual description...")
            visual_description = describe_visuals(file_content, mime_type)
            if isinstance(visual_description, str) and visual_description.startswith("Error:"):
                await file_input.close()
                raise HTTPException(status_code=500, detail=f"Failed to analyze image: {visual_description}")

            temp_chat = model.start_chat(history=[])
            summary_prompt = f"Based on the following detailed visual description of a skin condition, create a concise one-sentence summary statement suitable as an initial patient complaint:\n\n{visual_description}"
            initial_statement_raw = send_message_to_llm(temp_chat, summary_prompt)
            if isinstance(initial_statement_raw, str) and not initial_statement_raw.startswith("Error:"):
                initial_statement = f"Image analysis summary: {initial_statement_raw.strip()}"
            else:
                print("⚠️ Could not generate summary from visual description, using description directly.")
                initial_statement = f"Visual Description from Image:\n{visual_description}"

        elif mime_type in cfg.SUPPORTED_AUDIO_TYPES:
            print("Input is audio. Transcribing...")
            transcribed_text = transcribe_audio_vertex(file_content, mime_type)
            if isinstance(transcribed_text, str) and transcribed_text.startswith("Error:"):
                await file_input.close()
                raise HTTPException(status_code=500, detail=f"Failed to transcribe audio: {transcribed_text}")
            if not transcribed_text:
                await file_input.close()
                raise HTTPException(status_code=400, detail="Audio transcription resulted in empty text.")
            initial_statement = f"User audio transcription: {transcribed_text}"
            print(f"🎙️ Transcription: \"{transcribed_text}\"")

        else:
            await file_input.close()
            raise HTTPException(status_code=415, detail=f"Unsupported file type for initial assessment intake: {mime_type}. Use /analyze_report for PDF/DOCX/Image analysis.")

        await file_input.close()

    elif text_input:
        initial_statement = text_input.strip()
        if not initial_statement:
            raise HTTPException(status_code=400, detail="Text input cannot be empty.")
        print(f"Input is text: \"{initial_statement[:100]}...\"")

    if not initial_statement:
         raise HTTPException(status_code=500, detail="Failed to establish an initial statement from input.")

    return initial_statement, visual_description, file_content, mime_type


# --- API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    # ... (endpoint remains the same) ...
        """ Root endpoint providing basic API information. """
        return {
            "message": "Welcome to the DermaAI API.",
            "version": app.version,
            "endpoints": {
                "/docs": "This API documentation.",
                "/generate_questions": "POST: Generate follow-up questions based on initial statement/symptoms.",
                "/assess": "POST: Perform a full assessment based on initial text or image/audio.",
                "/analyze_report": "POST: Analyze text from an uploaded PDF/DOCX/Image report.",
                "/continue_conversation": "POST: Continue an existing conversation using a session ID.",
                "/generate_report_pdf": "POST: Generate a PDF report from assessment results."
            }
        }

@app.post("/generate_questions", response_model=QuestionResponse, tags=["Assessment Steps"])
async def get_diagnostic_questions_endpoint(request: QuestionRequest = Body(...)):
    # ... (endpoint remains the same) ...
    """
    Generates potential diagnostic questions based on an initial statement and optional symptoms.
    """
    print("\n--- Generate Questions Request ---")
    start_time = time.time()
    temp_chat_session = model.start_chat(history=[]) # Temporary session for this step

    symptoms_to_use = request.symptoms
    if not symptoms_to_use:
        print("Extracting symptoms from statement...")
        symptoms_to_use = extract_symptoms(temp_chat_session, request.statement)
        if not symptoms_to_use: symptoms_to_use = [] # Ensure list

    print(f"Generating questions for statement: \"{request.statement[:100]}...\" with symptoms: {symptoms_to_use}")
    questions = generate_diagnosis_questions(temp_chat_session, symptoms_to_use, request.statement)
    processing_time = round(time.time() - start_time, 2)

    if questions:
        print(f"✅ Questions generated successfully in {processing_time}s.")
        return QuestionResponse(
            message="Diagnostic questions generated successfully.",
            processing_time_seconds=processing_time,
            questions=questions,
            statement_processed=request.statement,
            symptoms_used=symptoms_to_use
        )
    else:
        print(f"❌ Failed to generate questions in {processing_time}s.")
        raise HTTPException(status_code=500, detail="Failed to generate diagnostic questions from the LLM.")


@app.post("/assess", response_model=AssessmentResponse, tags=["Assessment Steps"])
async def create_assessment_endpoint(
    background_tasks: BackgroundTasks,
    text_input: Optional[str] = Form(None),
    file_input: Optional[UploadFile] = File(None)
):
    # ... (endpoint remains the same) ...
    """
    Performs a full simulated assessment based on initial text, image, or audio input.
    """
    print("\n--- Full Assessment Request ---")
    start_time = time.time()
    if not text_input and not file_input:
        raise HTTPException(status_code=400, detail="Provide either 'text_input' or 'file_input'.")
    if text_input and file_input:
        raise HTTPException(status_code=400, detail="Provide only one of 'text_input' or 'file_input'.")

    try:
        initial_statement, visual_description, _, _ = await process_input(text_input, file_input)
    except HTTPException as e:
        raise e
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error processing input: {e}")

    chat_session = model.start_chat(history=[])

    try:
        print("Extracting symptoms...")
        symptoms = extract_symptoms(chat_session, initial_statement)

        print("Getting initial diagnosis...")
        init_diagnosis = get_initial_diagnosis(chat_session)
        if not init_diagnosis: raise HTTPException(status_code=500, detail="Failed to get initial analysis from LLM.")

        print("Performing deep research...")
        research_texts = perform_deep_research(init_diagnosis)

        print("Getting final assessment...")
        final_assessment = get_final_diagnosis(chat_session, research_texts)
        if not final_assessment: raise HTTPException(status_code=500, detail="Failed to get final assessment from LLM.")

        print("Generating report markdown...")
        report_markdown = generate_report_markdown(final_assessment, visual_description)

        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        print(f"--- Assessment Complete (Duration: {processing_time}s) ---")

        return AssessmentResponse(
            message="Assessment completed successfully.",
            processing_time_seconds=processing_time,
            final_assessment=final_assessment,
            report_markdown=report_markdown,
            initial_diagnosis=init_diagnosis,
            extracted_symptoms=symptoms,
            visual_description_if_any=visual_description,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"🚨 Unexpected Error during assessment processing: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during assessment: {e}")


@app.post("/analyze_report", response_model=ReportAnalysisResponse, tags=["Utilities"])
async def analyze_report_endpoint(report_file: UploadFile = File(...)):
    # ... (endpoint remains the same) ...
    """
    Analyzes an uploaded report file (PDF, DOCX, Image) using OCR/text extraction
    and asks the LLM to summarize it in simple terms.
    """
    print("\n--- Analyze Report Request ---")
    start_time = time.time()

    max_size = 20 * 1024 * 1024
    size = await report_file.read()
    await report_file.seek(0)
    if len(size) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {max_size // 1024 // 1024}MB.")

    file_bytes = await report_file.read()
    filename = report_file.filename
    mime_type = report_file.content_type
    if not mime_type or mime_type == 'application/octet-stream':
        mime_type, _ = mimetypes.guess_type(filename)
    await report_file.close()

    if not mime_type:
         raise HTTPException(status_code=415, detail="Could not determine file MIME type.")
    print(f"Analyzing file: {filename}, Type: {mime_type}")

    analysis_result = analyze_report_file(file_bytes, mime_type)
    processing_time = round(time.time() - start_time, 2)

    if analysis_result.startswith("Error:"):
        print(f"❌ Report analysis failed in {processing_time}s: {analysis_result}")
        status_code = 500 if "LLM" in analysis_result or "unexpected" in analysis_result else 400
        raise HTTPException(status_code=status_code, detail=analysis_result)
    else:
        print(f"✅ Report analysis successful in {processing_time}s.")
        return ReportAnalysisResponse(
            message="Report analyzed successfully.",
            processing_time_seconds=processing_time,
            analysis_summary=analysis_result,
            file_processed=filename,
            mime_type=mime_type
        )


@app.post("/continue_conversation", response_model=ConversationResponse, tags=["Conversation"])
async def continue_conversation_endpoint(request: ConversationRequest = Body(...)):
    """
    Continues an existing conversation or starts a new one.
    Uses simple in-memory storage (NOT FOR PRODUCTION).
    """
    print("\n--- Continue Conversation Request ---")
    start_time = time.time()
    session_id = request.session_id
    user_query = request.query

    if session_id and session_id in conversation_histories:
        print(f"Continuing session: {session_id}")
        chat_session = conversation_histories[session_id]
        if not isinstance(chat_session, ChatSession):
             print(f"⚠️ Invalid object found in history for session {session_id}. Starting new session.")
             session_id = str(uuid.uuid4())
             chat_session = model.start_chat(history=[])
    else:
        session_id = str(uuid.uuid4()) # Generate new ID
        print(f"Starting new session: {session_id}")
        chat_session = model.start_chat(history=[]) # Initialize a new ChatSession

    # --- Call the new function from Agents/chatbot.py ---
    llm_response = generate_chat_response(chat_session, user_query)

    # Store the updated session object (send_message_to_llm updated its history)
    conversation_histories[session_id] = chat_session
    # Simple logging to see history grow (won't show full content easily)
    print(f"Stored history for session {session_id}. Turn count: {len(chat_session.history)}")

    processing_time = round(time.time() - start_time, 2)

    if llm_response.startswith("Error:"):
        print(f"❌ LLM error during conversation in {processing_time}s: {llm_response}")
        # Return error response but include session_id
        return ConversationResponse(
            session_id=session_id,
            response=llm_response,
            processing_time_seconds=processing_time
        )
    else:
        print(f"✅ Conversation response generated successfully in {processing_time}s.")
        return ConversationResponse(
            session_id=session_id,
            response=llm_response,
            processing_time_seconds=processing_time
        )

@app.post("/generate_report_pdf", tags=["Reporting"])
async def create_report_pdf_endpoint(request: PdfRequest = Body(...)):
    # ... (endpoint remains the same) ...
    """
    Generates a downloadable PDF report from assessment results.
    """
    print("\n--- PDF Generation Request ---")
    start_time = time.time()
    report_markdown = request.report_markdown

    try:
        if not report_markdown:
            print("Generating markdown for PDF...")
            report_markdown = generate_report_markdown(request.final_assessment, request.visual_description)
            if report_markdown.startswith("Error:"):
                raise HTTPException(status_code=500, detail=f"Failed to generate report content: {report_markdown}")

        print("Generating PDF from markdown...")
        pdf_bytes = generate_pdf_from_md(report_markdown)
        processing_time = round(time.time() - start_time, 2)

        if pdf_bytes:
            print(f"✅ PDF generated successfully in {processing_time}s.")
            filename = f"Simulated_Dermatology_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            print(f"❌ PDF generation failed in {processing_time}s (likely WeasyPrint issue).")
            raise HTTPException(status_code=500, detail="Failed to generate PDF report. Check server logs and WeasyPrint dependencies.")

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"🚨 Unexpected Error during PDF generation: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during PDF generation: {e}")


# --- Run Instruction (for local development) ---
if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True, workers=1)