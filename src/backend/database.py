from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from fastapi import Depends

# setup the db connection
load_dotenv()

DATABASE_URL: str = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

engine: object = create_engine(url=DATABASE_URL)
session_local: object = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base: object = declarative_base()


# provide dependency for fastapi - session factory
def get_db():
    db = session_local()

    try:
        yield db
    finally:
        db.close()
