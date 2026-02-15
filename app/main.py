from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

VERSION = "0.1.0"

app = FastAPI(
    title="Video Trans API",
    description="API for video transcription and translation",
    version=VERSION
)

# Configure CORS
# NOTE: For production, restrict allow_origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to AI Video Trans API",
        "version": VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
