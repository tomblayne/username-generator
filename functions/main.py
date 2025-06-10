import google.generativeai as genai
import os
from firebase_functions import params
from firebase_functions.https_fn import on_request
from firebase_admin import initialize_app

# Constants
GEMINI_API_KEY_PARAM_NAME = "GEMINI_API_KEY"
GEMINI_MODEL_NAME = 'gemini-pro'

# Initialize Firebase Admin SDK if not already initialized
initialize_app()

@on_request() # Note the parentheses
def generate_username(request):
    # Accessing the API key using params module
    # Ensure you set GEMINI_API_KEY_PARAM_NAME as a Firebase Functions environment variable
    # Example command to set it: firebase functions:secrets:set YOUR_GEMINI_API_KEY_NAME="YOUR_GEMINI_API_KEY"
    try:
        api_key = params.String(GEMINI_API_KEY_PARAM_NAME).value
    except Exception as e:
        # Handle case where API key is not set, especially during local testing
        print(f"Warning: {GEMINI_API_KEY_PARAM_NAME} not found as a parameter. Trying environment variable. Error: {e}")
        api_key = os.environ.get(GEMINI_API_KEY_PARAM_NAME)
        if not api_key:
            return ('API key not configured. Please set GEMINI_API_KEY as a Firebase Function parameter or environment variable.', 500, {'Access-Control-Allow-Origin': '*'})


    # CORS preflight handling for HTTP requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Actual request handling for GET/POST
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    request_json = request.get_json(silent=True)
    if request_json and 'prompt' in request_json:
        prompt = request_json['prompt']
    else:
        return ('Please provide a "prompt" in the request body.', 400, headers)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    try:
        response = model.generate_content(prompt)
        # Assuming response.text is the content you want to return
        return (response.text, 200, headers)
    except Exception as e:
        # Log the full exception for debugging
        print(f"Error generating content: {e}")
        return (f"Error generating content: {e}", 500, headers)