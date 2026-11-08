from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One-to-many relationship with downloads
    downloads = relationship("Download", back_populates="owner")


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    webhook_url = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    description = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    tags = Column(String, nullable=True)
    progress = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship to user
    owner = relationship("User", back_populates="downloads")
