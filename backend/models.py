from datetime import datetime
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


class Settings(SQLModel, table=True):
    """Configuration globale de l'instance."""
    id: Optional[int] = Field(default=None, primary_key=True)
    # ntfy
    ntfy_url: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    ntfy_token: Optional[str] = None  # pour topics privés
    # Rappel quotidien aidant
    daily_reminder_enabled: bool = False
    daily_reminder_time: str = "09:00"  # HH:MM
    daily_reminder_message: str = "N'oubliez pas de mettre à jour le message du jour pour Agnès."
    # Mode nuit
    night_start: str = "21:30"
    night_end: str = "07:00"
    # Home Assistant
    ha_url: str = ""
    ha_token: str = ""
    # Météo
    latitude: float = 48.8566
    longitude: float = 2.3522


class Photo(SQLModel, table=True):
    """Photos du diaporama famille."""
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str
    caption: Optional[str] = None
    display_order: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class HAEntity(SQLModel, table=True):
    """Entité Home Assistant à afficher sur l'écran."""
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_id: str          # ex: sensor.temperature_salon
    label: str              # ex: Température salon
    icon: str = "🌡️"        # emoji affiché
    unit: str = ""          # ex: °C, %, km/h
    display_order: int = 0


class ScreenEvent(SQLModel, table=True):
    """Journal de connexion/déconnexion de l'écran patient."""
    id: Optional[int] = Field(default=None, primary_key=True)
    event: str  # "connected" | "disconnected"
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
