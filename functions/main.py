import google.generativeai as genai
import os
# from firebase_functions import params # REMOVE THIS IMPORT
from firebase_functions.https_fn import on_request
from firebase_admin import initialize_app

# Constants
GEMINI_API_KEY_PARAM_NAME = "GEMINI_API_KEY"
GEMINI_MODEL_NAME = 'gemini-pro'

# Initialize Firebase Admin SDK if not already initialized
initialize_app()

@on_request()
def generate_username(request):
    # Ensure all responses (including errors) have CORS headers
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # Accessing the API key directly from environment variables (where secrets are exposed)
    # This replaces the entire 'try-except' block for params.String
    api_key = os.environ.get(GEMINI_API_KEY_PARAM_NAME) # This is the correct way
    if not api_key:
        return ('API key not configured. Please ensure GEMINI_API_KEY is set as a secret and exposed as an environment variable.', 500, response_headers)

    # CORS preflight handling for HTTP requests
    if request.method == 'OPTIONS':
        return ('', 204, response_headers)

    # Actual request handling for GET/POST
    if request.method == 'POST':
        request_json = request.get_json(silent=True)
        if not request_json or 'prompt' not in request_json:
            return ('Please provide a "prompt" in the request body.', 400, response_headers)

        prompt = request_json['prompt']

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)

        try:
            full_gemini_prompt = f"Generate 1 unique and creative username based on these keywords/themes: '{prompt}'. Keep it concise, single word if possible, and suitable for online use. Return only the username, no extra text, numbering, or explanations."
            
            response = model.generate_content(full_gemini_prompt)
            
            generated_username = response.text.strip()
            
            if generated_username:
                response_headers['Content-Type'] = 'text/plain' 
                return (generated_username, 200, response_headers)
            else:
                return ("No username could be generated for the given prompt. Please try a different one.", 500, response_headers)

        except Exception as e:
            print(f"Error generating content: {e}")
            response_headers['Content-Type'] = 'text/plain'
            return (f"Error generating content: {e}. Please check your Firebase Function logs.", 500, response_headers)
    else:
        response_headers['Content-Type'] = 'text/plain'
        return ("Method Not Allowed", 405, response_headers)