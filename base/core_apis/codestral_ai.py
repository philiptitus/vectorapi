import requests
import json
from django.conf import settings


api_key = settings.CODESTRAL_API_KEY

def call_chat_endpoint(data, api_key=api_key):
    url = "https://codestral.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}, {response.text}"

if __name__ == "__main__":
    prompt = input("Enter your prompt: ")

    # Prepare data payload for the chat endpoint
    data = {
        "model": "codestral-latest",
        "messages": [{"role": "user", "content": prompt}]
    }

    # Call the chat endpoint
    response = call_chat_endpoint(data)

    if isinstance(response, dict):
        # Extract and print only the AI's response content
        ai_response = response['choices'][0]['message']['content'].strip()
        # Find the starting and ending indices of the code snippet
        start_index = ai_response.find('```') + 3
        end_index = ai_response.rfind('```')
        # Extract the code snippet
        code_snippet = ai_response[start_index:end_index].strip()
        # Print the code snippet
        print(code_snippet)
    else:
        # Print the error message
        print(response)
