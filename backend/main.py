from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import UPLOAD_DIR, BROWSER_PROFILE_DIR

app = FastAPI(
    title="Multi-Platform Social Video Publisher",
    description="Local web app to publish short-form vertical videos sequentially via Playwright",
    version="1.0.0"
)

# Enable CORS for local React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend server is running."""
    return {"status": "ok"}
