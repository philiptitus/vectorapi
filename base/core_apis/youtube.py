from googleapiclient.discovery import build
from django.conf import settings

def get_youtube_links(search_query, max_results=5):
    api_key = settings.YOUTUBE_API_KEY  # Replace with your YouTube Data API key
    youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)  # Disable cache

    # Search for videos matching the query
    search_response = youtube.search().list(
        q=search_query,
        part="id,snippet",
        maxResults=max_results,
        type="video"
    ).execute()

    video_links = []
    for item in search_response.get("items", []):
        video_id = item["id"]["videoId"]
        video_title = item["snippet"]["title"]
        video_url = f"https://www.youtube.com/embed/{video_id}"
        video_links.append((video_title, video_url))

    return video_links
