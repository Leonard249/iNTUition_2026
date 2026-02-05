#!/usr/bin/env python3
"""
Run script for A11y Overlay Backend
"""
import uvicorn
import sys
import os

def main():
    """Start the FastAPI server"""
    
    # Get port from environment or default
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Development mode detection
    reload = os.getenv("ENV", "development") == "development"
    
    print(f"🚀 Starting A11y Overlay API")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🔄 Reload: {reload}")
    print(f"🤖 Ollama: http://localhost:11434")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"🔧 Health: http://{host}:{port}/health")
    print("-" * 50)
    
    # Start uvicorn with proper configuration
    uvicorn.run(
        "main:app",  # Import string format
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()