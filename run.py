import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("=================================================================")
    print("   [*] SmartCart AI - Conversational Merchant Growth & Checkout  ")
    print("=================================================================")
    print("Starting server at: http://localhost:8000")
    print("Interactive Swagger Docs: http://localhost:8000/docs")
    print("Frontend UI: http://localhost:8000/")
    print("=================================================================")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
