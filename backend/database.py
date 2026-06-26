import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "/data/snoozolene.db")
engine = create_engine(f"sqlite:///{DATABASE_URL}", echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
