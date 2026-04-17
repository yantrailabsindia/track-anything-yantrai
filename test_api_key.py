import os
from google import genai

# Isolate credentials so it doesn't pick up gcloud auth
if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

api_key = os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY_HERE")
client = genai.Client(vertexai=True, project="mohit-first-organised", location="us-central1")

print("Sending test prompt using new google-genai package...")
response = client.models.generate_content(
    model='gemini-1.5-flash-001',
    contents='Hello! What is your model version?'
)
print("Response received:")
print(response.text)
