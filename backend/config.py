from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://pooniavikram348:qiVRLYNEI78dSGTl@cluster0.s6zc7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")




