import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Staging directory for video uploads
UPLOAD_DIR = BASE_DIR / "temp_uploads"

# Persistent user profile directory for Playwright browser automation
BROWSER_PROFILE_DIR = BASE_DIR / ".browser_profile"

# Execution logs directory
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# API Keys and External Configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Server Ports
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
