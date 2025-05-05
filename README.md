<div align="center">
  <h1>  DermaAI API: Simulated Dermatology Assistant</h1>
  <a class="header-badge" target="_blank" href="https://www.linkedin.com/in/khatoonintech/">
  <img src="https://img.shields.io/badge/style--5eba00.svg?label=LinkedIn&logo=linkedin&style=social">
  </a>
  

<sub>Author:
<a href="https://www.linkedin.com/in/Khatoonintech/" target="_blank">Ayesha Noreen</a><br>
<small> Agentic AI & Automation Enginer @DevRolin </small>
</sub>
<br>
<br>
<br>
	  
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Adjust license if needed -->

</div>

---




## Overview

DermaAI API is a backend application built with FastAPI that simulates a consultation with an AI-powered dermatology assistant. It leverages Google's Vertex AI Gemini models for analysis and response generation, Google Custom Search for information retrieval, and various Python libraries for processing different input types (text, audio, images, documents).

The primary goal of this project is to demonstrate the integration of various AI services and backend technologies to create a sophisticated assistant capable of:

*   Performing initial assessments based on user descriptions or media uploads.
*   Generating relevant follow-up questions.
*   Conducting simulated "deep research" using web searches.
*   Analyzing uploaded medical reports (PDF, DOCX, Images via OCR).
*   Engaging in conversational follow-up, augmented by web search context.
*   Generating summary reports in Markdown and PDF formats.

**Disclaimer:** This is a simulation for educational and demonstration purposes only. It does **NOT** provide real medical advice, diagnosis, or treatment recommendations. Always consult a qualified healthcare professional for any medical concerns.

## Table of Contents

1.  [Overview](#overview)
2.  [Table of Contents](#table-of-contents)
3.  [Features](#features)
4.  [Architecture](#architecture)
5.  [Technology Stack](#technology-stack)
6.  [Project Structure](#project-structure)
7.  [Requirements](#requirements)
    *   [Python Version](#python-version)
    *   [System Dependencies](#system-dependencies)
    *   [Python Packages](#python-packages)
8.  [Setup and Installation](#setup-and-installation)
    *   [Prerequisites](#prerequisites)
    *   [Clone Repository](#clone-repository)
    *   [Environment Variables (.env)](#environment-variables-env)
    *   [Install Dependencies](#install-dependencies)
    *   [Run Locally](#run-locally)
9.  [API Endpoints](#api-endpoints)
10. [State Management Note](#state-management-note)
11. [Deployment (Render Example)](#deployment-render-example)
12. [Conclusion](#conclusion)
13. [Future Improvements](#future-improvements)
14. [License](#license)

## Features

*   **Multi-modal Input:** Accepts initial concerns via text, audio (MP3, WAV, FLAC, OGG), or images (PNG, JPG, WEBP).
*   **Symptom Extraction:** Uses LLM to identify key symptoms from user input.
*   **Follow-up Question Generation:** Dynamically generates relevant questions to clarify the user's condition (`/generate_questions`).
*   **Conversational Interaction:** Allows users to chat with the AI assistant, maintaining context and augmenting responses with real-time web search results (`/continue_conversation`).
*   **Simulated Assessment:** Performs a multi-step assessment including initial analysis, web research on potential conditions, and a final summarized assessment (`/assess`).
*   **Report Analysis:** Extracts text from uploaded PDF, DOCX, or image files (using OCR) and uses LLM to summarize the report in simple terms (`/analyze_report`).
*   **Report Generation:** Creates Markdown and downloadable PDF reports summarizing the assessment (`/generate_report_pdf`).
*   **Configurable AI Model:** Uses Vertex AI Gemini models (configurable in `CONFIGURATION.py`).
*   **Modular Agent Design:** Logic is separated into distinct agent modules (Diagnosis, Search, Chatbot, etc.).

## Architecture

The application follows a modular, agent-based architecture built upon the FastAPI framework:

1.  **FastAPI Core:** Handles incoming HTTP requests, routing, request validation (using Pydantic), and response formatting.
2.  **API Endpoints (`app.py`):** Define the specific routes (e.g., `/assess`, `/continue_conversation`) and orchestrate calls to different agents and utilities.
3.  **Agents (`Agents/` directory):** Encapsulate specific functionalities:
    *   `UserIntakeAgent`: Processes initial visual input.
    *   `DIAGNOSIS`: Handles symptom extraction, question generation, initial/final diagnosis logic using LLM.
    *   `SEARCHENGINEAgent`: Interacts with Google Custom Search API and scrapes web content.
    *   `chatbot`: Manages conversational replies, including search augmentation.
    *   `ReportAnalysisAgent`: Extracts text from documents/images and triggers LLM analysis.
    *   `ReportingAgent`: Generates Markdown and PDF reports.
4.  **Initialization (`Initialization.py`):** Sets up core components like the Vertex AI client, Generative Model instance, Speech Recognizer, and provides core utility functions (`send_message_to_llm`, `parse_json_response`, `transcribe_audio_vertex`).
5.  **Configuration (`CONFIGURATION.py`):** Manages static configuration (model names, safety settings) and loads sensitive API keys and project IDs from environment variables (`.env` file).
6.  **State Management (In-Memory - `app.py`):** A simple dictionary is used to store conversation history for the `/continue_conversation` endpoint. **This is NOT production-ready.**

Most endpoints operate statelessly, processing input and returning a result. The `/continue_conversation` endpoint relies on the in-memory `conversation_histories` dictionary to maintain state between calls using a `session_id`.

## Technology Stack

*   **Backend Framework:** FastAPI
*   **Programming Language:** Python 3.9+
*   **AI Model:** Google Vertex AI (Gemini Flash/Pro models)
*   **Web Search:** Google Custom Search API
*   **Speech-to-Text:** SpeechRecognition library (using `recognize_google()`)
*   **Audio Handling:** Pydub (requires ffmpeg/libav for some formats)
*   **PDF Generation:** WeasyPrint (requires Pango/Cairo system libraries)
*   **PDF Text Extraction:** PyPDF2
*   **DOCX Text Extraction:** python-docx
*   **Image OCR:** pytesseract & Pillow (requires Tesseract OCR engine)
*   **Web Scraping:** Requests, BeautifulSoup4
*   **Configuration:** python-dotenv
*   **Serving:** Uvicorn

## Project Structure

```
.
DermaAI_backend/
│
├── .env                           # Environment variables and configuration
├── __init__.py                   # Makes the directory a Python package
├── app.py                        # Main FastAPI application
├── CONFIGURATION.py              # Global configuration settings
├── Initialization.py             # Model and service initialization
├── requirements.txt              # Project dependencies
├── README.md                     # Project documentation
│
└── Agents/                       # Agent modules directory
    ├── __init__.py              # Makes Agents a package
    ├── UserIntakeAgent.py       # Handles initial user input processing
    ├── SearchEngineAgent.py     # Web search and information retrieval
    ├── Diagnosis.py             # Diagnostic logic and assessment
    ├── ReportingGenerationAgent.py  # Report generation functionality
    ├── ReportingAnalysisAgent.py    # Report analysis and insights
    └── chatbot.py               # Conversational interface logic
```

## Requirements

### Python Version

*   Python 3.9 or higher is recommended.

### System Dependencies

These external libraries **must be installed** on the system where the application runs (your local machine, Docker container, or Render instance). Installation commands may vary based on your OS (examples below for Debian/Ubuntu).

1.  **For WeasyPrint (PDF Generation):**
    *   Pango, Cairo, GDK-PixBuf, Fontconfig, libffi
    *   Example (`apt-get`):
        ```bash
        sudo apt-get update && sudo apt-get install -y \
            build-essential python3-dev python3-pip python3-venv \
            libffi-dev libcairo2-dev libpango1.0-dev libpangocairo-1.0-0 \
            libgdk-pixbuf2.0-dev shared-mime-info \
            fontconfig
        ```

2.  **For pytesseract (Image OCR):**
    *   Tesseract OCR Engine
    *   Example (`apt-get`):
        ```bash
        sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-eng # Add other languages if needed (e.g., tesseract-ocr-fra)
        ```

3.  **For Pydub (Audio Conversion):**
    *   FFmpeg or Libav (FFmpeg recommended)
    *   Example (`apt-get`):
        ```bash
        sudo apt-get update && sudo apt-get install -y ffmpeg
        ```

### Python Packages

All required Python packages are listed in `requirements.txt`. Install them using pip:

```bash
pip install -r requirements.txt
```

## Setup and Installation

### Prerequisites

1.  **Google Cloud Project:** Create or select a Google Cloud project.
2.  **Enable APIs:** In your Google Cloud project, enable the following APIs:
    *   Vertex AI API
    *   Custom Search API
3.  **Vertex AI Setup:** Ensure Vertex AI is set up in a supported region.
4.  **Custom Search Engines:**
    *   Create a **Web Search** engine using the Google Programmable Search Engine control panel. Note its **Search engine ID**.
    *   Create an **Image Search** engine (enable "Image search" in the settings). Note its **Search engine ID**.
5.  **API Key:** Create a Google Cloud API Key with permissions to access Vertex AI and Custom Search APIs. **Restrict this key** appropriately for security.

### Clone Repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### Environment Variables (.env)

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file and fill in your actual credentials obtained in the Prerequisites step:

    ```dotenv
    # .env file - Store your secrets here
    # Make sure this file is in your .gitignore

    GOOGLE_API_KEY="your_google_cloud_api_key_here"
    SEARCH_ENGINE_ID="your_google_web_search_engine_id_here"
    IMAGE_ENGINE_ID="your_google_image_search_engine_id_here"
    VERTEX_PROJECT_ID="your_gcp_project_id_here"
    VERTEX_LOCATION="your_vertex_ai_region_here" # e.g., us-central1
    ```

    **SECURITY:** Never commit your `.env` file to version control. Ensure `.env` is listed in your `.gitignore` file.

### Install Dependencies

1.  **Install System Dependencies:** Install the libraries mentioned in the [System Dependencies](#system-dependencies) section using your system's package manager (e.g., `apt-get`, `brew`).
2.  **Create Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Run Locally

1.  Start the FastAPI application using Uvicorn:
    ```bash
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
    ```
    *   `--reload`: Automatically restarts the server on code changes (for development).
    *   `--host 0.0.0.0`: Makes the server accessible on your network.
    *   `--port 8000`: Specifies the port (adjust if needed).

2.  Access the API documentation (Swagger UI) in your browser at `http://127.0.0.1:8000/docs`. You can interact with the API endpoints directly from this interface.

## API Endpoints

Refer to the interactive documentation at `/docs` for detailed request/response schemas and to try out the API.

*   **`GET /`**: Basic API information and endpoint list.
*   **`POST /generate_questions`**: Takes an initial statement (and optional symptoms) and returns potential follow-up questions.
*   **`POST /assess`**: Performs the full assessment flow based on initial text/image/audio input. Returns the final assessment and report markdown.
*   **`POST /analyze_report`**: Accepts a file upload (PDF, DOCX, Image), extracts text, and returns an LLM-generated summary in simple terms.
*   **`POST /continue_conversation`**: Takes a `query` and an optional `session_id`. Continues an existing chat session or starts a new one, returning the LLM's response. (Uses non-persistent in-memory state).
*   **`POST /generate_report_pdf`**: Takes the `final_assessment` data (from `/assess` response) and generates a downloadable PDF report.

## State Management Note

The `/continue_conversation` endpoint uses a simple Python dictionary (`conversation_histories` in `app.py`) to store `ChatSession` objects between requests.

**⚠️ This implementation is NOT suitable for production environments!**
*   State is lost if the server restarts.
*   It will not work correctly if you run multiple Uvicorn workers (`--workers > 1`).
*   Memory usage can grow indefinitely.

For production or multi-user scenarios, replace this with a persistent storage solution like:
*   **Redis:** Fast key-value store suitable for caching session data.
*   **Database:** PostgreSQL, MongoDB, etc., to store session history more permanently.
*   **Server-Side Session Libraries:** Integrate with FastAPI session management extensions.

## Deployment (Render Example)

To deploy this application to a platform like Render:

1.  **Push to Git:** Ensure your code (excluding `.env`) is pushed to a Git repository (GitHub, GitLab).
2.  **Create Render Web Service:** Connect your Git repository to a new Web Service on Render.
3.  **Build Command:** Render should automatically detect `requirements.txt`. Set the build command if needed: `pip install -r requirements.txt`
4.  **Start Command:** Set the start command: `uvicorn app:app --host 0.0.0.0 --port $PORT` (Render sets the `$PORT` environment variable).
5.  **Environment Variables:** In the Render service settings, add all the variables defined in your `.env` file (`GOOGLE_API_KEY`, `VERTEX_PROJECT_ID`, etc.) as **Environment Variables**. **Do not upload the `.env` file.**
6.  **System Dependencies:** This is the most critical step for Render. You need to ensure the system dependencies for WeasyPrint, Tesseract, and FFmpeg are installed. Options include:
    *   **Using Docker:** Create a `Dockerfile` based on a Python image (e.g., `python:3.10-slim`), add `RUN apt-get update && apt-get install -y ...` commands to install the system packages, copy your application code, and set the `CMD`. Set Render to use your Dockerfile.
    *   **Render Native Environment + Build Script:** If not using Docker, check if Render's native environment includes the necessary libraries. If not, you might need a `render.yaml` blueprint or a build script (`render-build.sh`) specified in Render settings that runs the `apt-get install` commands before `pip install`. Consult Render's documentation for installing system packages.
7.  **Deploy:** Trigger a deploy on Render. Check the deploy logs carefully for any errors related to package installation or application startup.

## Conclusion

The DermaAI API provides a robust demonstration of integrating Large Language Models (Vertex AI Gemini), search capabilities, and various file processing techniques within a modern Python web framework (FastAPI). It showcases how these technologies can be combined to build sophisticated, multi-functional AI assistants. While powerful, remember the crucial disclaimer: **this tool is for informational simulation only and cannot replace professional medical consultation.**

## Future Improvements

*   **Persistent State Management:** Replace in-memory chat history with Redis or a database.
*   **Multi-Turn Assessment:** Modify the `/assess` flow to properly incorporate answers from `/generate_questions`.
*   **Frontend UI:** Develop a web-based user interface to interact with the API.
*   **Enhanced Error Handling:** Provide more specific error codes and messages.
*   **OCR Preprocessing:** Implement image preprocessing steps (e.g., binarization, deskewing) before OCR for better accuracy.
*   **Asynchronous Operations:** Utilize FastAPI's `async` capabilities more deeply, especially for long-running tasks like complex analysis or scraping (e.g., using `background_tasks` more extensively or libraries like `httpx` for async requests).
*   **Testing:** Add unit and integration tests.
*   **CI/CD Pipeline:** Set up automated testing and deployment.
*   **Security Hardening:** Implement rate limiting, authentication/authorization, and more robust input validation.

## License

<!-- Choose a license -->
This project is licensed under the MIT License - see the LICENSE file for details .

---

<div align="center">
<h3>For any query/help ,please contact our developer:</h3>  
Developer : <a href="https://www.linkedin.com/in/Khatoonintech/" target="_blank">Ayesha Noreen</a><br>
	<small> Agentic AI & Automation Engr @DevRolin </small>
<br> <a href="https://www.github.com/Khatoonintech/" target="_blank"> Don't forget to ⭐ our repo </a><br>


</div>


