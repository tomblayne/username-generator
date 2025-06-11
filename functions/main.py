import os
import google.generativeai as genai
from firebase_functions.https_fn import on_request
from firebase_admin import initialize_app

# Constants
GEMINI_API_KEY_ENV_NAME = "GEMINI_API_KEY" # Use this constant for the environment variable name
GEMINI_MODEL_NAME = 'models/gemini-pro'

# Initialize Firebase Admin SDK if not already initialized
initialize_app()

@on_request(
    # No 'secrets' argument here, as we are managing secrets via firebase.json
    region="us-central1", # Recommended to specify a region for your function
)
def generate_username(request):
    response_headers = {
        'Access-Control-Allow-Origin': 'https://user-name-generator.web.app',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    if request.method == 'OPTIONS':
        print("Handling OPTIONS preflight request.")
        return ('', 204, response_headers)

    # Access the API key directly from environment variables
    api_key = os.environ.get(GEMINI_API_KEY_ENV_NAME)

    # --- DEBUGGING LINE: TEMPORARILY PRINT API KEY VALUE TO LOGS ---
    # WARNING: This exposes your API key in logs. REMOVE AFTER DEBUGGING!
    # Truncate for display in logs if it's a real key, or just print its presence
    print(f"DEBUG: Value of GEMINI_API_KEY (first 5 chars): '{api_key[:5] if api_key else 'None'}'")
    # --- END DEBUGGING LINE ---

    if not api_key:
        print(f"ERROR: API key '{GEMINI_API_KEY_ENV_NAME}' not configured in environment.")
        response_headers['Content-Type'] = 'text/plain'
        return (f"API key not configured. Please ensure {GEMINI_API_KEY_ENV_NAME} is set as a secret and linked to the function via firebase.json.", 500, response_headers)

    genai.configure(api_key=api_key)

    # --- Logging for model availability ---
    try:
        print("Attempting to list available Gemini models...")
        available_models = [m.name for m in genai.list_models()]
        print(f"Successfully listed models. Total: {len(available_models)}")
        print(f"Available models: {available_models}")
        if GEMINI_MODEL_NAME in available_models:
            print(f"'{GEMINI_MODEL_NAME}' IS present in the list of available models.")
        else:
            print(f"'{GEMINI_MODEL_NAME}' IS NOT present in the list of available models. Please check exact model name and API permissions.")
    except Exception as e:
        import traceback
        print(f"ERROR listing models: {e}")
        print(traceback.format_exc())
    # --- END Logging ---

    if request.method == 'POST':
        try:
            print(f"Received POST request. Content-Type: {request.headers.get('Content-Type')}")
            request_json = request.get_json(silent=True)
            print(f"Parsed JSON from request: {request_json}")

            if not request_json or 'prompt' not in request_json:
                print("ERROR: No 'prompt' key found in request JSON or JSON is invalid.")
                response_headers['Content-Type'] = 'text/plain'
                return ('Please provide a "prompt" in the request body.', 400, response_headers)

            prompt = str(request_json['prompt']).strip()
            print(f"Extracted and stripped prompt: '{prompt}' (Type: {type(prompt)})")

            if not prompt:
                print("ERROR: Extracted prompt is empty after stripping.")
                response_headers['Content-Type'] = 'text/plain'
                return ('Error: Prompt is empty. Please provide valid content.', 400, response_headers)

            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            print(f"Attempting to use Gemini Model: {GEMINI_MODEL_NAME}")

            full_gemini_prompt = (
                f"Generate 1 unique and creative username based on these keywords/themes: '{prompt}'. "
                "Keep it concise, single word if possible, and suitable for online use. "
                "Return only the username, no extra text, numbering, or explanations."
            )
            print(f"Sending prompt to Gemini API: '{full_gemini_prompt}'")

            response = model.generate_content(full_gemini_prompt)

            print(f"Received response from Gemini API: {response}")
            if response.text:
                print(f"Gemini response.text: '{response.text}'")
            else:
                print("WARNING: Gemini response.text is empty or not available.")

            generated_username = response.text.strip()
            print(f"Generated username after stripping: '{generated_username}'")

            if generated_username:
                response_headers['Content-Type'] = 'text/plain'
                return (generated_username, 200, response_headers)
            else:
                print("ERROR: No username could be extracted from Gemini response text.")
                response_headers['Content-Type'] = 'text/plain'
                return ("No username could be generated for the given prompt. Please try a different one.", 500, response_headers)

        except Exception as e:
            import traceback
            print(f"UNCAUGHT EXCEPTION IN POST handler: {e}")
            print(traceback.format_exc())
            response_headers['Content-Type'] = 'text/plain'
            return (f"An unexpected error occurred in the function: {e}. Please check Cloud Function logs for details.", 500, response_headers)

    else:
        print(f"Received unsupported HTTP method: {request.method}")
        response_headers['Content-Type'] = 'text/plain'
        return ("Method Not Allowed", 405, response_headers)
    