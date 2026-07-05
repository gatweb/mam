import os
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "/data/snoozolene.db")
engine = create_engine(f"sqlite:///{DATABASE_URL}", echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
    _migrate()


def reinit_engine():
    """Recrée le pool de connexions après un restore (sinon SQLite lit l'ancien fichier)."""
    engine.dispose()


def _migrate():
    """Ajoute les colonnes manquantes pour les mises à jour de schéma."""
    migrations = [
        ("person", "birth_date", "TEXT"),
        ("person", "next_visit", "TEXT"),
        ("person", "allow_video_call", "INTEGER DEFAULT 0"),
        ("settings", "alarm_enabled", "INTEGER DEFAULT 0"),
        ("settings", "alarm_time", "TEXT DEFAULT '08:00'"),
        ("settings", "alarm_days", "TEXT DEFAULT '0,1,2,3,4,5,6'"),
        ("settings", "alarm_ha_media_player", "TEXT DEFAULT ''"),
        ("settings", "alarm_music_url", "TEXT DEFAULT ''"),
        ("settings", "ha_url", "TEXT DEFAULT ''"),
        ("settings", "ha_token", "TEXT DEFAULT ''"),
        ("settings", "ha_position", "TEXT DEFAULT 'bottom'"),
        ("settings", "latitude", "REAL DEFAULT 48.8566"),
        ("settings", "longitude", "REAL DEFAULT 2.3522"),
        ("settings", "jitsi_url", "TEXT DEFAULT 'https://meet.jit.si'"),
        ("settings", "fall_webhook_token", "TEXT DEFAULT ''"),
        ("haentity", "state_on_label", "TEXT"),
        ("haentity", "state_off_label", "TEXT"),
        ("haentity", "state_on_color", "TEXT"),
        ("haentity", "state_off_color", "TEXT"),
    ]
    with engine.connect() as conn:
        for table, col, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass  # colonne déjà présente
