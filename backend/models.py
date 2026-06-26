from datetime import datetime, time
from typing import Optional
from sqlmodel import SQLModel, Field


class CareRecipient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    reassurance_message: str = "Tu es en sécurité."
    photo_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Household(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str  # "chez Gaëtan"
    address: Optional[str] = None
    photo_path: Optional[str] = None
    reassurance_message: str = "Tu es chez toi. Tu es en sécurité."


class Person(SQLModel, table=True):
    """Proches de la personne accompagnée."""
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    relation: str  # "ton fils", "ta sœur"
    photo_path: Optional[str] = None
    message: Optional[str] = None
    next_visit: Optional[str] = None  # texte libre : "dimanche après-midi"
    is_primary_caregiver: bool = False
    allow_video_call: bool = False


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    event_date: str  # ISO date YYYY-MM-DD
    event_time: Optional[str] = None  # HH:MM
    recurrence: Optional[str] = None  # "none" | "daily" | "weekly:0,2,4" | "monthly:15"
    recurrence_end: Optional[str] = None  # ISO date YYYY-MM-DD, None = sans fin
    person_name: Optional[str] = None  # "le kiné Marc"
    message_before: Optional[str] = None
    message_during: Optional[str] = None
    message_after: Optional[str] = None
    priority: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FAQ(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    answer: str
    photo_path: Optional[str] = None
    display_order: int = 0
    active: bool = True


class DailyMessage(SQLModel, table=True):
    """Message du jour envoyé par l'aidant (mise à jour immédiate)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
