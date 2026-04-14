import uvicorn
from dotenv import load_dotenv
import os

if __name__ == "__main__":
    load_dotenv()
    # Now that main.py is in the root, we call "main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
