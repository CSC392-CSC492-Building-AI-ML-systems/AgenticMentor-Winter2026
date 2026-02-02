"""Main FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="AgenticMentor API",
    description="AI Project Mentor",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "AgenticMentor API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
