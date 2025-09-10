"""
Simple FastAPI test server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="FuzeAgent Mock Server - Test",
    description="Simple test server",
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

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "FuzeAgent Mock Server - Test",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Test organizations endpoint
@app.get("/organizations")
async def get_organizations():
    return {
        "items": [
            {
                "id": "1",
                "name": "Test Organization",
                "description": "A test organization",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "page": 1,
        "size": 20,
        "pages": 1
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
