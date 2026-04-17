import vertexai
from vertexai.generative_models import GenerativeModel
import os

project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "mohit-first-organised")

print(f"Initializing Vertex AI for project: {project_id}")
vertexai.init(project=project_id, location="us-central1")

print("Loading model: gemini-1.0-pro")
model = GenerativeModel("gemini-1.0-pro")

print("Sending test prompt...")
response = model.generate_content("Hello! What is your model version?")
print("Response received:")
print(response.text)
