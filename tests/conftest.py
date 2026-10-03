import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

@pytest.fixture
def db():
    engine=create_engine("sqlite:///:memory:",connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine); session=sessionmaker(bind=engine,expire_on_commit=False)()
    try: yield session
    finally: session.close(); Base.metadata.drop_all(engine); engine.dispose()
