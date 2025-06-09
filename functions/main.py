import os
import functions_framework
import google.generativeai as genai
from flask import jsonify, request

# Configure the Gemini API with the key stored in Firebase Functions config
# Make sure you have run: firebase functions:config:set gemini.api_key="YOUR_API_KEY"
try:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # In a real app, you might want to log this error more formally
    # or have a fallback
    pass # Allow the function to still deploy even if API key isn't found during config

# Initialize the Gemini model
# You can choose other models if needed, e.g., 'gemini-pro'
model = genai.GenerativeModel('gemini-pro')

@functions_framework.http
def generate_username(request):
    """HTTP Cloud Function that generates a username using the Gemini API.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    # Set CORS headers for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    request_json = request.get_json(silent=True)
    request_args = request.args

    prompt = ''
    if request_json and 'prompt' in request_json:
        prompt = request_json['prompt']
    elif request_args and 'prompt' in request_args:
        prompt = request_args['prompt']

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400, headers

    try:
        # Construct the full prompt for the AI
        full_prompt = f"Generate a creative and unique username (single word or hyphenated, no spaces) based on the following description: '{prompt}'. Provide only the username, no extra text or explanations."

        # Generate content using the Gemini model
        response = model.generate_content(full_prompt)

        # Extract the generated text
        generated_username = response.text.strip()

        # Clean up the username if it contains unwanted characters or phrases from the AI
        # This is important as AI can sometimes add unwanted intros/outros
        # Example cleaning:
        generated_username = generated_username.replace("\"", "").replace("'", "").replace("Generated Username: ", "").replace("Here's a username: ", "").split('\n')[0].strip()

        # If the username contains spaces, replace them with hyphens, and ensure it's a single "word"
        generated_username = generated_username.replace(" ", "-")

        return jsonify({"username": generated_username}), 200, headers

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return jsonify({"error": "Failed to generate username", "details": str(e)}), 500, headers