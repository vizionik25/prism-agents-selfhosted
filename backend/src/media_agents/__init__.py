from .main import app

__all__ = ["app", "main"]


def main() -> None:
    """Entry point for the `media-agents` console script."""
    import uvicorn

    uvicorn.run(
        "media_agents.main:app",
        host="0.0.0.0",
        port=8200,
        reload=True,
    )
