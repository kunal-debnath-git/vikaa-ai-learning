import uvicorn
from dotenv import load_dotenv
import os

if __name__ == "__main__":
    load_dotenv()
    port = int(os.environ.get("PORT", 9000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
