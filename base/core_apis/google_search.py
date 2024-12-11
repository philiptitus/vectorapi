from googleapiclient.discovery import build
from django.conf import settings

def search_google(query):
    # Configure the API key and the Custom Search Engine ID
    api_key = settings.GOOGLE_SEARCH_API_KEY
    cse_id = settings.GOOGLE_CUSTOM_SEARCH_ENGINE_ID

    # Build the service with cache disabled
    service = build("customsearch", "v1", developerKey=api_key, cache_discovery=False)

    # Perform the search
    res = service.cse().list(q=query, cx=cse_id).execute()

    # Extract the search results
    search_items = res.get("items", [])

    # Format the search results
    results = []
    for item in search_items:
        result = {
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "link": item.get("link")
        }
        results.append(result)

    return results
