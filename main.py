from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os

app = FastAPI(
    title="Safwaan AI Studio - Viral Video Money Printing Machine",
    description="AI-powered viral video generation and automated social media posting for maximum revenue",
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
        ],
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "message": "Safwaan AI Studio is running"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify app is working."""
    return {
        "message": "Safwaan AI Studio Test Endpoint",
        "env_vars": {
            "port": os.getenv("PORT", "8000"),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "railway_env": os.getenv("RAILWAY_ENVIRONMENT", "not_set")
        },
        "features_available": [
            "FastAPI",
            "Database (Coming Soon)",
            "AI Services (Coming Soon)",
            "Social Media (Coming Soon)"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )