import uvicorn
import logging
from dotenv import load_dotenv
import os

print("booting uvicorn dev server ...")

# load env variables
load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        os.getenv("MODULE_NAME"),
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT")),
        reload=bool(os.getenv("DEV_MODE", "0") == "1"),
        # ssl_keyfile=os.getenv("SSL_KEYFILE"),
        # ssl_certfile=os.getenv("SSL_CERTFILE"),
    )
