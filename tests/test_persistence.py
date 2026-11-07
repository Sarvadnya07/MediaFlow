import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Download, User


def test_sqlite_models_and_persistence(tmp_path):
    db_file = tmp_path / "test_downloads.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    TestingSession = sessionmaker(bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    session = TestingSession()
    user = User(username="mediadock_user", email="user@mediadock.io", hashed_password="hashed_pw_123")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.role == "user"

    download = Download(
        url="https://example.com/video.mp4",
        title="Sample Video",
        filepath="/downloads/sample.mp4",
        status="completed",
        progress=100,
        user_id=user.id
    )
    session.add(download)
    session.commit()
    session.refresh(download)

    assert download.id is not None
    assert download.owner.username == "mediadock_user"
    assert len(user.downloads) == 1

    session.close()
