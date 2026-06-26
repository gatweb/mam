import os
import asyncio
from datetime import datetime, date
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from PIL import Image

from database import get_session, init_db
from models import CareRecipient, Household, Person, Event, FAQ, DailyMessage

MEDIA_DIR = os.getenv("MEDIA_DIR", "/data/media")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(f"{MEDIA_DIR}/photos", exist_ok=True)
    os.makedirs(f"{MEDIA_DIR}/videos", exist_ok=True)
    init_db()
    _seed_if_empty()
    yield


app = FastAPI(title="Snoozolène API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

_ws_clients: list[WebSocket] = []


async def _broadcast(data: dict):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


# ── Seed ──────────────────────────────────────────────────────────────────────

def _seed_if_empty():
    from database import engine
    with Session(engine) as s:
        if s.exec(select(CareRecipient)).first():
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

        # Événements récurrents d'exemple
        s.add(Event(
            title="Kiné",
            event_date=next_monday,
            event_time="14:00",
            recurrence="weekly:0,2",  # lundi et mercredi
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
            recurrence="weekly:6",  # dimanche
            message_before="Sophie va appeler cet après-midi vers 15 h.",
            message_during="Sophie t'appelle ! Elle pense à toi.",
            message_after="Tu as parlé avec Sophie. Elle reviendra dimanche prochain.",
        ))

        # FAQ
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

        s.commit()


def _next_weekday(weekday: int) -> str:
    """Retourne la prochaine date d'un jour de la semaine (0=lundi)."""
    d = date.today()
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (d.replace(day=d.day + days_ahead)).isoformat()


# ── Résolution des récurrences ────────────────────────────────────────────────

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
    matching = [e for e in all_events if _event_matches_date(e, d)]
    return sorted(matching, key=lambda e: e.event_time or "")


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

    return {
        "recipient": recipient.model_dump() if recipient else None,
        "household": household.model_dump() if household else None,
        "people": [p.model_dump() for p in people],
        "events_today": [e.model_dump() for e in events],
        "faqs": [f.model_dump() for f in faqs],
        "daily_message": daily_msg.model_dump() if daily_msg else None,
        "server_time": datetime.now().isoformat(),
    }


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


# ── Seed reset (dev) ───────────────────────────────────────────────────────────

@app.post("/api/admin/reset-seed")
async def reset_seed(session: Session = Depends(get_session)):
    """Vide la base et recharge les données de démo."""
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
