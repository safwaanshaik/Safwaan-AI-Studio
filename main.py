from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Safwaan AI Studio - Viral Video Money Printing Machine",
    description="AI-powered viral video generation and automated social media posting",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with system status."""
    return {
        "message": "Safwaan AI Studio - Viral Video Money Printing Machine is running!",
        "version": "1.0.0",
        "status": "active",
        "features": [
            "AI Video Generation",
            "Automated Social Media Posting",
            "Trend Detection",
            "Revenue Tracking",
            "24/7 Money Making"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2025-10-22T12:36:39.540Z",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify app is working."""
    return {
        "message": "Test endpoint working!",
        "env_vars": {
            "port": os.getenv("PORT", "8000"),
            "python_version": os.sys.version,
            "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not_set")
        }
    }