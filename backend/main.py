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
from models import CareRecipient, Household, Person, Event, FAQ, DailyMessage, Settings, ScreenEvent
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

@app.get("/api/display")
def get_display_state(session: Session = Depends(get_session)):
    recipient = session.exec(select(CareRecipient)).first()
    household = session.exec(select(Household)).first()
    people = session.exec(select(Person)).all()
    faqs = session.exec(select(FAQ).where(FAQ.active == True).order_by(FAQ.display_order)).all()
    events = _get_events_for_date(session, date.today())
    daily_msg = session.exec(
        select(DailyMessage).order_by(DailyMessage.created_at.desc())
    ).first()
    settings = session.exec(select(Settings)).first() or Settings()

    return {
        "recipient": recipient.model_dump() if recipient else None,
        "household": household.model_dump() if household else None,
        "people": [p.model_dump() for p in people],
        "events_today": [e.model_dump() for e in events],
        "faqs": [f.model_dump() for f in faqs],
        "daily_message": daily_msg.model_dump() if daily_msg else None,
        "night_start": settings.night_start,
        "night_end": settings.night_end,
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
