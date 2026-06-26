import os
import uuid
import asyncio
from datetime import datetime, date
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from PIL import Image

from database import get_session, init_db, engine
from models import CareRecipient, Household, Person, Event, FAQ, DailyMessage, Settings, ScreenEvent, HAEntity, Photo
from notify import send_notification, notify_screen_disconnected, notify_screen_reconnected, notify_daily_reminder

MEDIA_DIR = os.getenv("MEDIA_DIR", "/data/media")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(f"{MEDIA_DIR}/photos", exist_ok=True)
    os.makedirs(f"{MEDIA_DIR}/videos", exist_ok=True)
    init_db()
    _seed_if_empty()
    _setup_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Snoozolène API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# ── WebSocket pool + état écran ────────────────────────────────────────────────

_ws_clients: set[WebSocket] = set()
_screen_online = False
_screen_disconnect_task: asyncio.Task | None = None


async def _broadcast(data: dict):
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


def _get_settings() -> Settings:
    with Session(engine) as s:
        return s.exec(select(Settings)).first() or Settings()


def _get_recipient_name() -> str:
    with Session(engine) as s:
        r = s.exec(select(CareRecipient)).first()
        return r.first_name if r else "la personne accompagnée"


async def _on_screen_disconnected():
    """Attend 60 s puis notifie si l'écran ne s'est pas reconnecté."""
    await asyncio.sleep(60)
    global _screen_online
    if not _screen_online:
        settings = _get_settings()
        await notify_screen_disconnected(settings, _get_recipient_name())
        with Session(engine) as s:
            s.add(ScreenEvent(event="disconnected"))
            s.commit()


# ── Scheduler ──────────────────────────────────────────────────────────────────

def _setup_scheduler():
    settings = _get_settings()
    _reschedule_daily_reminder(settings)


def _reschedule_daily_reminder(settings: Settings):
    scheduler.remove_all_jobs()
    if settings.daily_reminder_enabled and settings.ntfy_topic:
        h, m = settings.daily_reminder_time.split(":")
        scheduler.add_job(
            _run_daily_reminder,
            CronTrigger(hour=int(h), minute=int(m)),
            id="daily_reminder",
            replace_existing=True,
        )


async def _run_daily_reminder():
    settings = _get_settings()
    await notify_daily_reminder(settings)


# ── Seed ──────────────────────────────────────────────────────────────────────

def _seed_if_empty():
    with Session(engine) as s:
        if s.exec(select(CareRecipient)).first():
            # Toujours créer les Settings si absents
            if not s.exec(select(Settings)).first():
                s.add(Settings())
                s.commit()
            return

        today = date.today().isoformat()
        next_monday = _next_weekday(0)

        s.add(CareRecipient(
            first_name="Martine",
            reassurance_message="Tu es en sécurité. Gaëtan s'occupe de toi.",
        ))
        s.add(Household(
            display_name="chez Gaëtan",
            reassurance_message="Tu es chez Gaëtan, ton fils. Tu es en sécurité.",
        ))
        s.add(Person(
            first_name="Gaëtan",
            relation="ton fils",
            message="Je suis dans la maison ou au travail. Je reviens toujours.",
            is_primary_caregiver=True,
        ))
        s.add(Person(
            first_name="Sophie",
            relation="ta sœur",
            message="Je pense à toi. Je viens te voir dimanche.",
            next_visit="dimanche après-midi",
        ))
        s.add(Event(
            title="Kiné",
            event_date=next_monday,
            event_time="14:00",
            recurrence="weekly:0,2",
            message_before="Le kiné vient cet après-midi à 14 h. Tu n'as rien à préparer.",
            message_during="Le kiné est là. Gaëtan lui ouvrira la porte.",
            message_after="Le kiné est passé. Tout s'est bien passé.",
        ))
        s.add(Event(
            title="Déjeuner",
            event_date=today,
            event_time="12:30",
            recurrence="daily",
            message_before="Le déjeuner est prêt à 12 h 30.",
            message_during="C'est l'heure du déjeuner.",
            message_after="Tu as bien déjeuné.",
        ))
        s.add(Event(
            title="Appel de Sophie",
            event_date=today,
            event_time="15:00",
            recurrence="weekly:6",
            message_before="Sophie va appeler cet après-midi vers 15 h.",
            message_during="Sophie t'appelle ! Elle pense à toi.",
            message_after="Tu as parlé avec Sophie. Elle reviendra dimanche prochain.",
        ))
        for order, (q, a) in enumerate([
            ("Est-ce que je rentre chez moi ?",
             "Tu es chez Gaëtan pour être accompagnée. Tu es en sécurité ici."),
            ("Quand revient Sophie ?",
             "Sophie vient te voir dimanche après-midi. Elle pense à toi."),
            ("Que vais-je faire aujourd'hui ?",
             "Aujourd'hui tu restes à la maison. Il n'y a rien à préparer."),
            ("Où est Gaëtan ?",
             "Gaëtan est dans la maison ou au travail. Il revient toujours."),
            ("Est-ce que je dors ici cette nuit ?",
             "Oui, ta chambre est prête. Tu dors ici, tu es bien installée."),
        ]):
            s.add(FAQ(question=q, answer=a, display_order=order))
        s.add(Settings())
        s.commit()


def _next_weekday(weekday: int) -> str:
    d = date.today()
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (d.replace(day=d.day + days_ahead)).isoformat()


# ── Récurrences ────────────────────────────────────────────────────────────────

def _event_matches_date(event: Event, d: date) -> bool:
    rec = event.recurrence or "none"
    if rec == "none" or not rec:
        return event.event_date == d.isoformat()
    if event.event_date and d.isoformat() < event.event_date:
        return False
    if event.recurrence_end and d.isoformat() > event.recurrence_end:
        return False
    if rec == "daily":
        return True
    if rec.startswith("weekly:"):
        days = [int(x) for x in rec.split(":")[1].split(",")]
        return (d.isoweekday() - 1) in days
    if rec.startswith("monthly:"):
        return d.day == int(rec.split(":")[1])
    return False


def _get_events_for_date(session: Session, d: date) -> list[Event]:
    all_events = session.exec(select(Event)).all()
    return sorted(
        [e for e in all_events if _event_matches_date(e, d)],
        key=lambda e: e.event_time or ""
    )


# ── Display ────────────────────────────────────────────────────────────────────

_WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}
_WMO_LABELS = {
    0: "Ensoleillé", 1: "Peu nuageux", 2: "Nuageux", 3: "Couvert",
    45: "Brouillard", 48: "Brouillard",
    51: "Bruine", 53: "Bruine", 55: "Bruine forte",
    61: "Pluie faible", 63: "Pluie", 65: "Forte pluie",
    71: "Neige faible", 73: "Neige", 75: "Forte neige",
    80: "Averses", 81: "Averses", 82: "Averses fortes",
    95: "Orage", 96: "Orage", 99: "Orage violent",
}
_JOURS_COURT = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


async def _fetch_weather(settings: Settings) -> list[dict]:
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={settings.latitude}&longitude={settings.longitude}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min"
            f"&timezone=auto&forecast_days=7"
        )
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            data = r.json()["daily"]
            result = []
            for i, date_str in enumerate(data["time"]):
                code = data["weathercode"][i]
                d = datetime.fromisoformat(date_str)
                result.append({
                    "date": date_str,
                    "day": "Auj." if i == 0 else _JOURS_COURT[d.weekday()],
                    "icon": _WMO_ICONS.get(code, "🌡️"),
                    "label": _WMO_LABELS.get(code, ""),
                    "tmax": round(data["temperature_2m_max"][i]),
                    "tmin": round(data["temperature_2m_min"][i]),
                })
            return result
    except Exception:
        return []


async def _fetch_ha_states(settings: Settings, entities: list[HAEntity]) -> list[dict]:
    headers = {"Authorization": f"Bearer {settings.ha_token}"}
    base = settings.ha_url.rstrip("/")
    results = []
    async with httpx.AsyncClient(timeout=5) as client:
        for ent in entities:
            try:
                r = await client.get(f"{base}/api/states/{ent.entity_id}", headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    state = data.get("state", "")
                    results.append({
                        "entity_id": ent.entity_id,
                        "label": ent.label,
                        "icon": ent.icon,
                        "unit": ent.unit,
                        "state": state,
                    })
            except Exception:
                pass
    return results


@app.get("/api/display")
async def get_display_state(session: Session = Depends(get_session)):
    recipient = session.exec(select(CareRecipient)).first()
    household = session.exec(select(Household)).first()
    people = session.exec(select(Person)).all()
    faqs = session.exec(select(FAQ).where(FAQ.active == True).order_by(FAQ.display_order)).all()
    events = _get_events_for_date(session, date.today())
    daily_msg = session.exec(
        select(DailyMessage).order_by(DailyMessage.created_at.desc())
    ).first()
    settings = session.exec(select(Settings)).first() or Settings()

    photos = session.exec(select(Photo).order_by(Photo.display_order, Photo.uploaded_at)).all()
    ha_entities = session.exec(select(HAEntity).order_by(HAEntity.display_order)).all()
    weather = await _fetch_weather(settings)
    ha_states = []
    if ha_entities and settings.ha_url and settings.ha_token:
        ha_states = await _fetch_ha_states(settings, ha_entities)

    return {
        "recipient": recipient.model_dump() if recipient else None,
        "household": household.model_dump() if household else None,
        "people": [p.model_dump() for p in people],
        "events_today": [e.model_dump() for e in events],
        "faqs": [f.model_dump() for f in faqs],
        "daily_message": daily_msg.model_dump() if daily_msg else None,
        "night_start": settings.night_start,
        "night_end": settings.night_end,
        "ha_states": ha_states,
        "photos": [p.model_dump() for p in photos],
        "weather": weather,
        "server_time": datetime.now().isoformat(),
    }


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global _screen_online, _screen_disconnect_task
    await websocket.accept()
    _ws_clients.add(websocket)
    _screen_online = True

    # Annuler l'alerte de déconnexion en attente si l'écran revient
    if _screen_disconnect_task and not _screen_disconnect_task.done():
        _screen_disconnect_task.cancel()
        settings = _get_settings()
        if settings.ntfy_topic:
            asyncio.create_task(notify_screen_reconnected(settings, _get_recipient_name()))
        with Session(engine) as s:
            s.add(ScreenEvent(event="connected"))
            s.commit()

    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)
        # Si plus aucun écran connecté, démarrer le timer d'alerte
        if not _ws_clients:
            _screen_online = False
            _screen_disconnect_task = asyncio.create_task(_on_screen_disconnected())


# ── Settings ───────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings(session: Session = Depends(get_session)):
    s = session.exec(select(Settings)).first()
    if not s:
        s = Settings()
        session.add(s)
        session.commit()
        session.refresh(s)
    # Ne pas exposer le token en clair
    data = s.model_dump()
    data["ntfy_token"] = "***" if s.ntfy_token else ""
    return data


@app.put("/api/settings")
async def update_settings(data: dict, session: Session = Depends(get_session)):
    s = session.exec(select(Settings)).first()
    if not s:
        s = Settings()
    for k, v in data.items():
        if k == "ntfy_token" and v == "***":
            continue  # ne pas écraser avec le masque
        if hasattr(s, k):
            setattr(s, k, v)
    session.add(s)
    session.commit()
    _reschedule_daily_reminder(s)
    return {"ok": True}


@app.post("/api/settings/test-notification")
async def test_notification(session: Session = Depends(get_session)):
    s = session.exec(select(Settings)).first() or Settings()
    ok = await send_notification(
        s,
        title="🔔 Snoozolène — Test",
        message="Les notifications fonctionnent correctement.",
        priority="default",
        tags=["bell"],
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Échec : vérifiez l'URL et le topic ntfy.")
    return {"ok": True}


# ── Seed reset ─────────────────────────────────────────────────────────────────

@app.post("/api/admin/reset-seed")
async def reset_seed(session: Session = Depends(get_session)):
    for model in [DailyMessage, Event, FAQ, Person, Household, CareRecipient]:
        for item in session.exec(select(model)).all():
            session.delete(item)
    session.commit()
    _seed_if_empty()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


# ── Household ──────────────────────────────────────────────────────────────────

@app.get("/api/household")
def get_household(session: Session = Depends(get_session)):
    return session.exec(select(Household)).first()


@app.put("/api/household")
async def update_household(data: dict, session: Session = Depends(get_session)):
    h = session.exec(select(Household)).first()
    if not h:
        raise HTTPException(status_code=404)
    for k, v in data.items():
        if hasattr(h, k):
            setattr(h, k, v)
    session.add(h)
    session.commit()
    await _broadcast({"type": "refresh"})
    return h


# ── Daily message ──────────────────────────────────────────────────────────────

@app.post("/api/daily-message")
async def post_daily_message(data: dict, session: Session = Depends(get_session)):
    msg = DailyMessage(content=data["content"], author=data.get("author"))
    session.add(msg)
    session.commit()
    session.refresh(msg)
    await _broadcast({"type": "refresh"})
    return msg


# ── Events ─────────────────────────────────────────────────────────────────────

@app.get("/api/events")
def list_events(session: Session = Depends(get_session)):
    return session.exec(select(Event).order_by(Event.event_date, Event.event_time)).all()


@app.post("/api/events")
async def create_event(data: dict, session: Session = Depends(get_session)):
    event = Event(**{k: v for k, v in data.items() if hasattr(Event, k)})
    session.add(event)
    session.commit()
    session.refresh(event)
    await _broadcast({"type": "refresh"})
    return event


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404)
    session.delete(event)
    session.commit()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


# ── FAQ ────────────────────────────────────────────────────────────────────────

@app.get("/api/faqs")
def list_faqs(session: Session = Depends(get_session)):
    return session.exec(select(FAQ).order_by(FAQ.display_order)).all()


@app.post("/api/faqs")
async def create_faq(data: dict, session: Session = Depends(get_session)):
    faq = FAQ(**{k: v for k, v in data.items() if hasattr(FAQ, k)})
    session.add(faq)
    session.commit()
    session.refresh(faq)
    await _broadcast({"type": "refresh"})
    return faq


@app.delete("/api/faqs/{faq_id}")
async def delete_faq(faq_id: int, session: Session = Depends(get_session)):
    faq = session.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404)
    session.delete(faq)
    session.commit()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


# ── People ─────────────────────────────────────────────────────────────────────

@app.get("/api/people")
def list_people(session: Session = Depends(get_session)):
    return session.exec(select(Person)).all()


@app.post("/api/people")
async def create_person(data: dict, session: Session = Depends(get_session)):
    person = Person(**{k: v for k, v in data.items() if hasattr(Person, k)})
    session.add(person)
    session.commit()
    session.refresh(person)
    await _broadcast({"type": "refresh"})
    return person


@app.put("/api/people/{person_id}")
async def update_person(person_id: int, data: dict, session: Session = Depends(get_session)):
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404)
    for k, v in data.items():
        if hasattr(person, k):
            setattr(person, k, v)
    session.add(person)
    session.commit()
    await _broadcast({"type": "refresh"})
    return person


@app.delete("/api/people/{person_id}")
async def delete_person(person_id: int, session: Session = Depends(get_session)):
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404)
    session.delete(person)
    session.commit()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


# ── Photos diaporama ──────────────────────────────────────────────────────────

@app.get("/api/photos")
def list_photos(session: Session = Depends(get_session)):
    return session.exec(select(Photo).order_by(Photo.display_order, Photo.uploaded_at)).all()


@app.post("/api/photos")
async def upload_photo_slide(
    file: UploadFile = File(...),
    caption: str = "",
    session: Session = Depends(get_session),
):
    filename = f"{datetime.now().timestamp()}_{file.filename}"
    path = f"{MEDIA_DIR}/photos/{filename}"
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    try:
        img = Image.open(path)
        img.thumbnail((1920, 1920))
        img.save(path, quality=85, optimize=True)
    except Exception:
        pass
    count = len(session.exec(select(Photo)).all())
    photo = Photo(path=f"/media/photos/{filename}", caption=caption or None, display_order=count)
    session.add(photo)
    session.commit()
    session.refresh(photo)
    await _broadcast({"type": "refresh"})
    return photo


@app.put("/api/photos/{photo_id}")
async def update_photo(photo_id: int, data: dict, session: Session = Depends(get_session)):
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404)
    if "caption" in data:
        photo.caption = data["caption"] or None
    if "display_order" in data:
        photo.display_order = data["display_order"]
    session.add(photo)
    session.commit()
    await _broadcast({"type": "refresh"})
    return photo


@app.delete("/api/photos/{photo_id}")
async def delete_photo(photo_id: int, session: Session = Depends(get_session)):
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404)
    try:
        full_path = MEDIA_DIR + photo.path.replace("/media", "")
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception:
        pass
    session.delete(photo)
    session.commit()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


# ── Home Assistant ────────────────────────────────────────────────────────────

@app.get("/api/ha/entities")
def list_ha_entities(session: Session = Depends(get_session)):
    return session.exec(select(HAEntity).order_by(HAEntity.display_order)).all()


@app.post("/api/ha/entities")
async def create_ha_entity(data: dict, session: Session = Depends(get_session)):
    ent = HAEntity(**{k: v for k, v in data.items() if hasattr(HAEntity, k)})
    session.add(ent)
    session.commit()
    session.refresh(ent)
    await _broadcast({"type": "refresh"})
    return ent


@app.delete("/api/ha/entities/{entity_id}")
async def delete_ha_entity(entity_id: int, session: Session = Depends(get_session)):
    ent = session.get(HAEntity, entity_id)
    if not ent:
        raise HTTPException(status_code=404)
    session.delete(ent)
    session.commit()
    await _broadcast({"type": "refresh"})
    return {"ok": True}


@app.post("/api/ha/test")
async def test_ha_connection(session: Session = Depends(get_session)):
    s = session.exec(select(Settings)).first() or Settings()
    if not s.ha_url or not s.ha_token:
        raise HTTPException(status_code=400, detail="URL et token Home Assistant requis.")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{s.ha_url.rstrip('/')}/api/",
                headers={"Authorization": f"Bearer {s.ha_token}"},
            )
            if r.status_code == 200:
                return {"ok": True, "message": r.json().get("message", "Connecté")}
            raise HTTPException(status_code=400, detail=f"HA a répondu {r.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connexion impossible : {e}")


@app.get("/api/ha/search")
async def search_ha_entities(q: str = "", session: Session = Depends(get_session)):
    """Recherche d'entités HA par entity_id ou friendly_name."""
    s = session.exec(select(Settings)).first() or Settings()
    if not s.ha_url or not s.ha_token:
        raise HTTPException(status_code=400, detail="HA non configuré.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{s.ha_url.rstrip('/')}/api/states",
                headers={"Authorization": f"Bearer {s.ha_token}"},
            )
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="Impossible de lister les entités.")
            all_states = r.json()
            q_lower = q.lower()
            filtered = [
                {
                    "entity_id": s["entity_id"],
                    "friendly_name": s.get("attributes", {}).get("friendly_name", ""),
                    "state": s["state"],
                    "unit": s.get("attributes", {}).get("unit_of_measurement", ""),
                }
                for s in all_states
                if not q_lower or q_lower in s["entity_id"].lower()
                   or q_lower in s.get("attributes", {}).get("friendly_name", "").lower()
            ]
            return filtered[:50]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Appel vidéo ───────────────────────────────────────────────────────────────

@app.post("/api/video-call/start")
async def start_video_call(data: dict, session: Session = Depends(get_session)):
    person_id = data.get("person_id")
    person = session.get(Person, person_id) if person_id else None
    room = f"snoozolene-{uuid.uuid4().hex[:12]}"
    await _broadcast({
        "type": "video_call",
        "room": room,
        "person_name": person.first_name if person else None,
    })
    return {"room": room, "url": f"https://meet.jit.si/{room}"}


@app.post("/api/video-call/end")
async def end_video_call():
    await _broadcast({"type": "video_call_end"})
    return {"ok": True}


# ── Upload photo ───────────────────────────────────────────────────────────────

@app.post("/api/upload/photo")
async def upload_photo(file: UploadFile = File(...)):
    filename = f"{datetime.now().timestamp()}_{file.filename}"
    path = f"{MEDIA_DIR}/photos/{filename}"
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    try:
        img = Image.open(path)
        img.thumbnail((1920, 1920))
        img.save(path)
    except Exception:
        pass
    return {"path": f"/media/photos/{filename}"}
