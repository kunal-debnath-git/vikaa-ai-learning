import uvicorn
from dotenv import load_dotenv
import os

if __name__ == "__main__":
    load_dotenv()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
