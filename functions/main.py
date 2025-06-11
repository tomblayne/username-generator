import os
import google.generativeai as genai
from firebase_functions.https_fn import on_request
from firebase_admin import initialize_app

# Conditional import for params.Secret to handle local environment during build analysis.
# For actual deployment, the Cloud Functions runtime will have params.Secret available.
try:
    from firebase_functions import params
    # Define the secret directly using params.Secret for proper 2nd Gen secret management
    GEMINI_API_KEY_SECRET = params.Secret("GEMINI_API_KEY")
    # This will be used in genai.configure() and passed to secrets=[]
    api_key_value_source = GEMINI_API_KEY_SECRET
except ImportError:
    # Fallback for local development/analysis where params.Secret might not exist in the old firebase-functions version
    print("WARNING: 'firebase_functions.params.Secret' not found, falling back to os.environ.get for local analysis.")
    # For local analysis, we might not have the secret, so provide a placeholder or expect it from env vars
    GEMINI_API_KEY_SECRET = os.environ.get("GEMINI_API_KEY", "dummy_key_for_local_analysis")
    api_key_value_source = GEMINI_API_KEY_SECRET


# Constants
GEMINI_MODEL_NAME = 'models/gemini-pro' # Ensure this is 'models/gemini-pro'

# Initialize Firebase Admin SDK if not already initialized
# This will typically initialize using Application Default Credentials (service account)
initialize_app()

@on_request(
    # Link the secret here using the params.Secret object (if successfully imported).
    # This is crucial for Cloud Functions to inject the secret into the environment.
    # The conditional check ensures it only applies if params.Secret was actually loaded.
    secrets=[GEMINI_API_KEY_SECRET] if 'params' in locals() and isinstance(GEMINI_API_KEY_SECRET, params.Secret) else [],
    region="us-central1", # Recommended to specify a region
    # You can add other configurations like memory, timeout, etc., here if needed
    # memory=512,
    # timeout_sec=60,
)
def generate_username(request):
    # Ensure all responses (including errors) have CORS headers
    # Setting Access-Control-Allow-Origin to the exact frontend origin is best practice
    response_headers = {
        'Access-Control-Allow-Origin': 'https://user-name-generator.web.app', # Use your specific frontend URL here
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600' # Cache preflight for 1 hour
    }

    # CORS preflight handling for HTTP requests
    if request.method == 'OPTIONS':
        print("Handling OPTIONS preflight request.")
        return ('', 204, response_headers)

    # Accessing the API key's value based on whether params.Secret was used or not.
    # At runtime in Cloud Functions, GEMINI_API_KEY_SECRET will be a params.Secret object.
    # During local analysis/tests where params.Secret might be missing, it will be a string.
    if isinstance(api_key_value_source, genai.types.Secret): # Check if it's a params.Secret object (from genai.types)
        api_key = api_key_value_source.value() # Access the value from the Secret object
    else:
        # Fallback if params.Secret was not used (e.g., during local analysis/testing where it might not exist)
        # In this scenario, we assume the API key might be directly available as an environment variable.
        api_key = os.environ.get("GEMINI_API_KEY")


    # --- DEBUGGING LINE: TEMPORARILY PRINT API KEY VALUE TO LOGS ---
    # WARNING: This exposes your API key in logs. REMOVE AFTER DEBUGGING!
    # Truncate for display in logs if it's a real key, or just print its presence
    print(f"DEBUG: Value of GEMINI_API_KEY (first 5 chars): '{api_key[:5] if api_key else 'None'}'")
    # --- END DEBUGGING LINE ---

    if not api_key or api_key == "dummy_key_for_local_analysis":
        print(f"ERROR: API key 'GEMINI_API_KEY' not configured in environment.")
        response_headers['Content-Type'] = 'text/plain'
        return ('API key not configured. Please ensure GEMINI_API_KEY is set as a secret and linked to the function.', 500, response_headers)

    genai.configure(api_key=api_key)

    # --- Logging for model availability (if not already working) ---
    try:
        print("Attempting to list available Gemini models...")
        # Note: genai.list_models() sometimes needs explicit authentication config or broader permissions
        # if the default service account lacks the 'Generative Language API User' role.
        # This will also fail if the API key is invalid or not configured.
        available_models = [m.name for m in genai.list_models()] # Removed `if m.supported_generation_methods` for broader listing
        print(f"Successfully listed models. Total: {len(available_models)}")
        print(f"Available models: {available_models}")
        if GEMINI_MODEL_NAME in available_models:
            print(f"'{GEMINI_MODEL_NAME}' IS present in the list of available models.")
        else:
            print(f"'{GEMINI_MODEL_NAME}' IS NOT present in the list of available models. Please check exact model name and API permissions.")

        if 'gemini-pro' in available_models:
             print("'gemini-pro' (without 'models/') IS present in the list of available models.")
        else:
             print("'gemini-pro' (without 'models/') IS NOT present in the list of available models.")

    except Exception as e:
        import traceback
        print(f"ERROR listing models: {e}")
        print(traceback.format_exc()) # Print traceback for model listing error
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