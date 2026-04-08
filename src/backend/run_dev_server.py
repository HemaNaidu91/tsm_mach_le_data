import uvicorn
import logging
from dotenv import load_dotenv
import os

print("booting uvicorn dev server ...")

# load env variables
load_dotenv()

uvicorn.run(
    os.getenv("MODULE_NAME"),
    host=os.getenv("HOST"),
    port=os.getenv("PORT"),
    # ssl_keyfile=os.getenv("SSL_KEYFILE"),
    # ssl_certfile=os.getenv("SSL_CERTFILE"),
)
