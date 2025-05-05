# Agents/chatbot.py

import time
from typing import Optional

# Import necessary functions from other modules
# Core LLM interaction utility from Initialization
from Initialization import model, send_message_to_llm
from vertexai.generative_models import ChatSession # Import ChatSession

# Search capabilities from SEARCHENGINEAgent
from Agents.SearchEngineAgent import search_google, get_urls_from_search, scrape_urls



def generate_chat_response(chat_session: ChatSession, user_query: str) -> str:
    """
    Generates a conversational response using the LLM, potentially augmenting
    with web search results. Maintains the dermatologist persona set in the model's
    system instructions and uses the provided chat session history.

    Args:
        chat_session: The active ChatSession object containing conversation history.
        user_query: The latest message/query from the user.

    Returns:
        The LLM's response string, or an error string beginning with "Error:".
    """
    print(f"Processing chat query within Chatbot Agent: '{user_query[:100]}...'")

    search_context = ""
    max_search_chars = 5000 # Limit context size from search

    # --- 1. Perform Web Search (if available) ---
    print("  Performing web search for context...")
    try:
        # Using specific search_type="web"
        search_results = search_google(user_query, search_type="web", max_results=3)
        if search_results:
            urls = get_urls_from_search(search_results, max_urls=2)
            if urls:
                scraped_texts = scrape_urls(urls)
                if scraped_texts:
                    search_context = "\n\n".join(scraped_texts)
                    if len(search_context) > max_search_chars:
                            print(f"  Truncating search context from {len(search_context)} to {max_search_chars} chars.")
                            search_context = search_context[:max_search_chars] + "... [Truncated]"
                    print(f"  Added {len(search_context)} chars of context from web search.")
                else: print("  Web scraping yielded no text content.") # Optional log
            else: print("  No relevant URLs found in search results.") # Optional log
        else: print("  Web search returned no results.") # Optional log
    except Exception as search_e:
        print(f"  ⚠️ Error during web search/scraping: {search_e}")
        # Continue without search context on error

    # --- 2. Construct Prompt for LLM ---
    # The system instruction (set during model initialization) establishes the persona.
    # We provide the user query and any supplemental search context.
    if search_context:
        prompt = f"""
        User Query: "{user_query}"

        Potentially relevant context from a web search:
        --- START SEARCH CONTEXT ---
        {search_context}
        --- END SEARCH CONTEXT ---

        Considering our conversation history AND the search context above, please respond to the User Query. Maintain your persona as a helpful, board-certified dermatologist AI assistant and include necessary disclaimers.
        """
    else:
        # If no search context, just pass the user query directly
        # The LLM will use the history from the chat_session automatically
        prompt = user_query # Simpler prompt, relying on history and system instruction

    # --- 3. Send to LLM ---
    print("Sending query (with search context if available) to LLM via send_message_to_llm...")
    # Use the imported send_message_to_llm function and the passed chat_session
    llm_response = send_message_to_llm(chat_session, prompt)

    # --- 4. Handle Response ---
    # send_message_to_llm returns either the text response or an "Error: ..." string
    if isinstance(llm_response, str) and llm_response.startswith("Error:"):
        print(f"❌ LLM error reported by send_message_to_llm: {llm_response}")
        return llm_response
    elif not isinstance(llm_response, str) or not llm_response.strip():
        print("❌ LLM returned an empty or invalid response for chat query.")
        return "Error: Received an empty response from the assistant."
    else:
        print("✅ Chatbot Agent received valid LLM response.")
        # History in chat_session is automatically updated by the call to send_message_to_llm
        return llm_response.strip()