import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# 1. Load your .env credentials
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# 2. Select the latest supported AI Model and enforce JSON output
vis_model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})

def analyze_medical_image(image_path):
    # 3. Load the image from your computer
    try:
        image = Image.open(image_path)
    except FileNotFoundError:
        return {"error": "Could not find the image."}

    # 4. Define the instructions for the AI
    image_prompt = '''
    - Generate a very detailed medical description for the given image.
    - Identify and describe any relevant medical conditions, anomalies, or abnormalities present in the image.
    - Provide an overall API anomaly "score" from 0 to 100 representing the severity or confidence of the anomaly. (0 = normal, 100 = critical/high confidence).
    - IMPORTANT: Return output in valid JSON format exactly matching this schema:
      {
        "score": integer_between_0_and_100,
        "analysis": "string formatted in rich HTML (e.g., using <b> for bold titles, <ul>/<li> for lists, <br> for line breaks). Include relatable medical emojis (like 🩺, 🦴, ⚠️, ✅) to make the text engaging."
      }
    '''
    
    # 5. Ask the AI to generate content based on the Prompt & Image
    try:
        print("Analyzing image, please wait...")
        response = vis_model.generate_content([image_prompt, image])
        data = json.loads(response.text)
        # Ensure score is treated purely as an integer to prevent edge-case TypeErrors
        return {"score": int(data.get("score", 0)), "analysis": str(data.get("analysis", ""))}
    except Exception as e:
        return {"error": f"An error occurred while calling the AI: {e}"}
