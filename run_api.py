"""
Run the REST API server
"""
import uvicorn
from config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║      ALPACA Trading Bot - REST API Server           ║
    ╚══════════════════════════════════════════════════════╝

    API running at: http://{settings.api_host}:{settings.api_port}
    Documentation: http://{settings.api_host}:{settings.api_port}/docs

    Use X-API-Key header for authentication
    """)

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
