# Agents/DIAGNOSIS.py

import json
import time
from typing import List, Dict, Any, Optional

# Import necessary functions and objects from other modules
from Initialization import send_message_to_llm, parse_json_response, model
from Agents.SearchEngineAgent import search_google, get_urls_from_search, scrape_urls
from vertexai.generative_models import ChatSession # Import ChatSession

def extract_symptoms(chat_session: ChatSession, statement: str) -> List[str]:
    """Extracts symptoms from the user statement using the LLM."""
    prompt = f"""
    Patient statement: "{statement}"

    Review the patient statement above. Extract all the key **symptoms** mentioned (e.g., REDNESS, ITCHING, RASH, PAIN, BLISTERS, LESION, SCALY PATCH). Be specific.
    Return ONLY a JSON array of uppercase strings (e.g., ["RASH", "ITCHING","PAIN","BLISTERS"]). If no clear symptoms are mentioned, return an empty array [].
    Do not include explanations or any text outside the JSON array.
    """
    response_text = send_message_to_llm(chat_session, prompt)

    # Check for LLM errors first
    if isinstance(response_text, str) and response_text.startswith("Error:"):
        print(f"❌ LLM Error during symptom extraction: {response_text}")
        return [] # Return empty on error

    try:
        symptoms_data = parse_json_response(response_text)
        if isinstance(symptoms_data, list) and all(isinstance(s, str) for s in symptoms_data):
            print("✅ Extracted Symptoms:", symptoms_data)
            return symptoms_data
        elif isinstance(symptoms_data, dict) and "error" in symptoms_data:
             print(f"❌ Failed to parse symptoms JSON: {symptoms_data.get('raw_response', response_text)}")
             return []
        elif isinstance(symptoms_data, dict) and "warning" in symptoms_data:
             print(f"⚠️ LLM response for symptoms was not JSON: {symptoms_data.get('raw_response', response_text)}. Attempting interpretation.")
             potential_symptoms = [s.strip().upper() for s in response_text.split(',') if s.strip()]
             if potential_symptoms:
                 print(f"✅ Extracted Symptoms (interpreted): {potential_symptoms}")
                 return potential_symptoms
             return []
        else:
             print(f"⚠️ LLM returned unexpected format for symptoms: {symptoms_data}. Type: {type(symptoms_data)}. Defaulting to empty list.")
             return []

    except Exception as e: # Catch any other unexpected error during processing
        print(f"❌ Exception processing symptom extraction response: {e}")
        print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
        return []

def generate_diagnosis_questions(chat_session: ChatSession, symptoms: List[str], statement: str) -> Optional[List[str]]:
    """
    Generates follow-up questions based on extracted symptoms and statement using the LLM.
    Does NOT handle user input; returns the list of questions.

    Args:
        chat_session: The active chat session with the LLM.
        symptoms: A list of extracted symptoms.
        statement: The initial user statement or context.

    Returns:
        A list of question strings if successful, otherwise None.
    """
    if not symptoms:
        print("No specific symptoms identified to base questions on. Asking general questions.")
        symptoms_str = "a general skin concern" # Slightly better phrasing for prompt
    else:
        symptoms_str = ", ".join(symptoms)

    prompt = f"""
    Based on the patient mentioning symptoms like: {symptoms_str} and the initial statement: "{statement}".

    Generate **exactly 5** concise follow-up questions a dermatologist might ask to clarify the condition.
    Focus on clarifying: Severity, Duration, Triggers, Location/Spread, Associated factors (fever, etc.), Previous treatments/attempts.
    Phrase the questions clearly and directly as if asking a patient.
    Return ONLY a **strict JSON array** containing exactly 5 strings (the questions). Do not include numbering, introductions, or any other text outside the JSON array.
    Example Format: ["How long have you had these symptoms?", "On a scale of 1-10, how severe is the itching?", ...]
    """
    print("Generating follow-up questions via LLM...")
    response_text = send_message_to_llm(chat_session, prompt)

    # Check for LLM errors first
    if isinstance(response_text, str) and response_text.startswith("Error:"):
        print(f"❌ LLM Error during question generation: {response_text}")
        return None # Indicate failure

    try:
        questionnaire = parse_json_response(response_text)

        # Validate the response
        if isinstance(questionnaire, list) and len(questionnaire) == 5 and all(isinstance(q, str) for q in questionnaire):
            print("✅ Generated Questions:", questionnaire)
            
            return questionnaire
        
        elif isinstance(questionnaire, dict) and "error" in questionnaire:
             print(f"❌ Failed to parse questions JSON: {questionnaire.get('raw_response', response_text)}")
             return None
        else:
             print(f"⚠️ LLM did not return exactly 5 questions in a valid JSON list format.")
             print(f"--- Received: --- \n{questionnaire}\n-----------------")
             # Optionally, try to salvage if it's a list but wrong length? Or just fail.
             # For now, strict failure:
             return None # Indicate failure

    except Exception as e: # Catch JSONDecodeError, ValueError, AttributeError etc.
        print(f"❌ Exception processing LLM response for questions: {e}")
        print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
        return None # Indicate failure

def get_initial_diagnosis(chat_session: ChatSession) -> Optional[Dict[str, Any]]:
    """
    Performs initial diagnosis based on the conversation history in the chat session.
    Assumes the session history contains the initial statement, visual description (if any),
    and extracted symptoms (implicitly through prompts/responses).
    """
    prompt = """
    Based *only* on the preceding conversation history (initial statement, visual description if provided, extracted symptoms, and potentially user answers to questions if they were added to history), perform an **initial dermatological analysis**.

    Return a **strict JSON object** with these exact keys and value types:
    {
      "most_likely_diagnosis": "string", // The single most probable condition.
      "justification": "string", // Brief reasoning citing specific symptoms/history/visuals from the conversation.
      "confidence_percentage": integer, // Estimated confidence (0-100) in the most likely diagnosis.
      "differential_diagnosis": [ // List of 2-3 alternative possibilities.
        {
          "disease": "string", // Name of alternative condition.
          "reasoning": "string" // Why it's considered but less likely than the main diagnosis based on conversation.
        }
      ]
    }

    **Important:** Respond ONLY with the JSON object. Do not include greetings, explanations outside the JSON, or any medical advice. Adhere strictly to the JSON format. Include a disclaimer within the justification stating this is not a real diagnosis.
    """
    response_text = send_message_to_llm(chat_session, prompt)

    # Check for LLM errors first
    if isinstance(response_text, str) and response_text.startswith("Error:"):
        print(f"❌ LLM Error during initial diagnosis: {response_text}")
        return None # Indicate failure

    try:
        init_diagnosis = parse_json_response(response_text)

        # Validate structure
        if not isinstance(init_diagnosis, dict) or "error" in init_diagnosis:
             print(f"❌ Failed to parse initial diagnosis JSON: {init_diagnosis.get('raw_response', response_text)}")
             return None

        required_keys = ["most_likely_diagnosis", "justification", "confidence_percentage", "differential_diagnosis"]
        if not all(key in init_diagnosis for key in required_keys):
            print(f"❌ Initial diagnosis response missing required keys. Found: {list(init_diagnosis.keys())}")
            print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
            return None # Indicate failure
        if not isinstance(init_diagnosis.get("differential_diagnosis"), list):
            print(f"❌ Differential diagnosis is not a list in the response.")
            print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
            init_diagnosis["differential_diagnosis"] = [] # Default to empty list maybe? Or fail.
            # return None # Safer to fail here if list structure is critical
        # Check sub-elements if needed
        if isinstance(init_diagnosis.get("differential_diagnosis"), list):
            for item in init_diagnosis["differential_diagnosis"]:
                if not isinstance(item, dict) or not all(k in item for k in ["disease", "reasoning"]):
                     print(f"❌ Invalid item in differential diagnosis list: {item}")
                     # Decide how to handle: remove item, fail validation, etc.
                     # For now, let it pass but log warning. Could return None for stricter validation.

        print("✅ Initial Analysis Received.")
        return init_diagnosis
    except Exception as e:
        print(f"❌ Exception processing initial diagnosis response: {e}")
        print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
        return None # Indicate failure

def perform_deep_research(diagnosis_data: Optional[Dict[str, Any]]) -> List[str]:
    """Searches for articles on diagnoses and scrapes them."""
    if not diagnosis_data or not diagnosis_data.get('most_likely_diagnosis'):
        print("⚠️ Skipping deep research: No initial diagnosis data provided.")
        return []

    diagnoses_to_research = [diagnosis_data['most_likely_diagnosis']]
    diff_dx = diagnosis_data.get('differential_diagnosis', [])
    if isinstance(diff_dx, list):
         diagnoses_to_research.extend([d.get('disease') for d in diff_dx if isinstance(d, dict) and d.get('disease')])

    unique_diagnoses = list(set(filter(None, diagnoses_to_research)))

    if not unique_diagnoses:
        print("⚠️ Skipping deep research: No valid diagnoses identified to research.")
        return []

    print(f"\n🔬 Researching potential diagnoses: {', '.join(unique_diagnoses)}")
    all_scraped_text = []
    total_urls_to_scrape = 5
    urls_per_disease = max(1, total_urls_to_scrape // len(unique_diagnoses))

    for disease in unique_diagnoses:
        print(f"  Searching for articles on: {disease}")
        search_query = f'"{disease}" dermatology overview reliable source OR symptoms treatment'
        search_results = search_google(search_query, search_type="web", max_results=urls_per_disease * 2)
        article_urls = get_urls_from_search(search_results, max_urls=urls_per_disease)

        if article_urls:
            print(f"    Found {len(article_urls)} URLs for {disease}.")
            scraped_text = scrape_urls(article_urls)
            all_scraped_text.extend(scraped_text)
        else:
            print(f"    No relevant web search results found for {disease}.")
        time.sleep(1) # Pause between searches

    print(f"✅ Deep research complete. Total scraped text snippets: {len(all_scraped_text)}")
    return all_scraped_text

def get_final_diagnosis(chat_session: ChatSession, research_texts: List[str]) -> Optional[Dict[str, Any]]:
    """Generates the final diagnosis incorporating research findings into the chat session."""
    research_summary = "\n\n".join(research_texts)
    max_research_chars = 20000
    if len(research_summary) > max_research_chars:
        print(f"⚠️ Research text too long ({len(research_summary)} chars), truncating to {max_research_chars} for final analysis.")
        research_summary = research_summary[:max_research_chars]

    research_prompt = f"""
    --- Relevant Research Findings Start ---
    The following text snippets were gathered from web searches related to the potential diagnoses discussed. Review them carefully.
    {research_summary if research_summary else "No research data was available or retrieved."}
    --- Relevant Research Findings End ---

    Now, please synthesize the entire conversation history AND the research findings above to provide a refined final dermatological assessment.
    """
    print("Adding research context to conversation...")
    # Send research context, response isn't the final assessment itself
    _ = send_message_to_llm(chat_session, research_prompt)
    time.sleep(0.5) # Small pause

    final_prompt = f"""
    Based on the entire preceding conversation, including the initial consultation, potentially user answers to questions, and the recently added research findings, provide the **refined final dermatological assessment**.

    Return ONLY a **strict JSON object** with these exact keys:
    {{
      "final_diagnosis": "string", // The single best diagnosis after considering all information.
      "reasoning": "string", // Detailed justification integrating chat history (symptoms, visuals, answers) AND research findings. Mention consistency or contradictions found.
      "possible_causes_triggers": "string", // Likely causes or triggers based on all info gathered.
      "general_treatment_options": "string", // Common approaches (e.g., topical steroids, antifungals, lifestyle changes). DO NOT prescribe specific drugs or dosages. Explain concepts generally.
      "when_to_see_doctor": "string", // Specific indicators suggesting urgent or standard need for professional consultation (e.g., worsening symptoms, spreading rapidly, signs of infection like pus/fever, no improvement after X days, severe pain).
    }}

    Focus on clarity, accuracy based on the provided information, and responsible communication. Adhere strictly to the JSON format with no extra text or greetings.
    """
    response_text = send_message_to_llm(chat_session, final_prompt)

    # Check for LLM errors first
    if isinstance(response_text, str) and response_text.startswith("Error:"):
        print(f"❌ LLM Error during final assessment: {response_text}")
        return None # Indicate failure

    try:
        final_assessment = parse_json_response(response_text)

        # Validate structure
        if not isinstance(final_assessment, dict) or "error" in final_assessment:
             print(f"❌ Failed to parse final assessment JSON: {final_assessment.get('raw_response', response_text)}")
             return None

        required_keys = ["final_diagnosis", "reasoning", "possible_causes_triggers", "general_treatment_options", "when_to_see_doctor", "important_disclaimer"]
        if not all(key in final_assessment for key in final_assessment):
             print(f"❌ Final assessment response missing required keys. Found: {list(final_assessment.keys())}")
             print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
             return None # Indicate failure

        print("✅ Final Assessment Received.")
        return final_assessment
    except Exception as e:
        print(f"❌ Exception processing final assessment response: {e}")
        print(f"--- LLM Response was ---\n{response_text}\n--------------------------")
        return None # Indicate failure