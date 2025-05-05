# Agents/SEARCHENGINEAgent.py

import requests
import time
import re
from bs4 import BeautifulSoup
from CONFIGURATION import GOOGLE_API_KEY, SEARCH_ENGINE_ID, IMAGE_ENGINE_ID # Import necessary config

def search_google(query: str, search_type: str = "web", max_results: int = 5) -> dict | None:
    """
    Performs a search using Google Custom Search Engine API.

    Args:
        query: The search term.
        api_key: Google API Key.
        cse_id: Custom Search Engine ID.
        search_type: 'web' or 'image'.
        max_results: Number of results to request (API default is 10).

    Returns:
        The JSON response from the API as a dictionary, or None on error.
    """
    url = 'https://www.googleapis.com/customsearch/v1'
    cse_id = IMAGE_ENGINE_ID if search_type == 'image' else SEARCH_ENGINE_ID
    api_key = GOOGLE_API_KEY # Use the key from config

    if not api_key or not cse_id:
        print("❌ Error: Google API Key or CSE ID is missing in configuration.")
        return None

    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
        'num': max_results # Request specific number of results
    }
    if search_type == 'image':
        params['searchType'] = 'image'
        params['imgSize'] = 'medium' # Optional: filter image size

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 DermaAIClient/1.0",
        "Referer": "https://www.google.com/" # Good practice to include a referer
    }

    try:
        # Increased timeout for potentially slow API responses
        res = requests.get(url, params=params, headers=headers, timeout=15)
        res.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
        print(f"Google Search successful for '{query}' ({search_type}).")
        return res.json()
    except requests.exceptions.Timeout:
        print(f"❌ Timeout during Google Search API call for '{query}'.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during Google Search API call for '{query}': {e}")
        return None # Return None on error
    except Exception as e:
        print(f"❌ An unexpected error occurred during Google Search for '{query}': {e}")
        return None

def get_urls_from_search(search_results: dict | None, max_urls: int = 5) -> list[str]:
    """Extracts URLs from search results."""
    links = []
    if search_results and 'items' in search_results:
        for item in search_results['items'][:max_urls]: # Already limited by max_results in search_google, but belt-and-suspenders
            link = item.get('link') # Use .get for safety
            if link:
                links.append(link)
            # For image search, sometimes the image URL is in 'image': {'contextLink': ...} or directly in 'link'
            elif 'image' in item and item['image'].get('contextLink'):
                 links.append(item['image']['contextLink']) # Prefer context link if available
    return links

def scrape_urls(urls: list[str]) -> list[str]:
    """Scrapes text content from a list of URLs."""
    scraped_content = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 DermaAIClient/1.0"
    }
    # Basic consent cookie, may help bypass some simple blockers
    cookies = {"CONSENT": "YES+cb.20230101-01-p0.en+FX+111"}

    print(f"Attempting to scrape {len(urls)} URLs...")
    for i, link in enumerate(urls):
        print(f"  Scraping ({i+1}/{len(urls)}): {link[:80]}...")
        try:
            response = requests.get(link, headers=headers, cookies=cookies, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # Check content type - only parse HTML
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                print(f"    ⚠️ Skipping non-HTML content ({content_type}) at {link}")
                continue

            # Check for excessively large responses before parsing
            if len(response.content) > 5_000_000: # 5MB limit
                 print(f"    ⚠️ Skipping large file ({len(response.content)} bytes) at {link}")
                 continue

            soup = BeautifulSoup(response.content, 'html.parser') # Use response.content for correct encoding handling

            # Remove elements likely not containing main content
            for element in soup(["script", "style", "header", "footer", "nav", "aside", "form", "button", "iframe", "noscript"]):
                element.decompose()

            # Try finding common main content containers
            main_content = soup.find('main') or \
                           soup.find('article') or \
                           soup.find('div', class_=re.compile(r'(content|main|body|post|entry|article)', re.I)) or \
                           soup.find('div', id=re.compile(r'(content|main|body|article)', re.I))

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                # Fallback to body if no specific container found, be cautious
                body = soup.find('body')
                text = body.get_text(separator=' ', strip=True) if body else ""
                if not text:
                     print(f"    ⚠️ Could not find main content or body text at {link}")
                     continue # Skip if body is empty too

            # Clean up whitespace and limit length
            cleaned_text = ' '.join(text.split())
            if len(cleaned_text) > 100: # Only add if substantial content exists
                scraped_content.append(cleaned_text[:5000]) # Limit length per page
                # print(f"    ✅ Scraped ~{len(cleaned_text)} chars.")
            else:
                print(f"    ⚠️ Skipping - minimal text content found after cleaning at {link}")


        except requests.exceptions.Timeout:
             print(f"    ❌ Timeout scraping {link}")
        except requests.exceptions.RequestException as e:
            # Handle specific HTTP errors if needed (e.g., 403 Forbidden)
            print(f"    ❌ HTTP Error scraping {link}: {e}")
        except Exception as e: # Catch potential BeautifulSoup errors or others
            print(f"    ❌ Error processing content from {link}: {e}")

        time.sleep(0.75) # Be polite, slightly increased delay

    print(f"✅ Scraping finished. Retrieved content from {len(scraped_content)} URLs.")
    return scraped_content