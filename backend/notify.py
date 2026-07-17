"""Envoi de notifications via ntfy.sh ou instance auto-hébergée."""
import httpx
from models import Settings


async def send_notification(
    settings: Settings,
    title: str,
    message: str,
    priority: str = "default",  # min low default high urgent
    tags: list[str] | None = None,
    click: str | None = None,  # URL ouverte quand on appuie sur la notification
) -> bool:
    if not settings.ntfy_topic:
        return False

    url = f"{settings.ntfy_url.rstrip('/')}/{settings.ntfy_topic}"
    # ⚠️ httpx encode les en-têtes str en ASCII : tout titre contenant un
    # emoji ou un « — » lève UnicodeEncodeError — et comme l'appel est entouré
    # d'un try/except, la notification échouait SILENCIEUSEMENT. On passe donc
    # des en-têtes en bytes UTF-8 (ntfy les accepte, cf. sa documentation).
    headers: list[tuple[bytes, bytes]] = [
        (b"Title", title.encode("utf-8")),
        (b"Priority", priority.encode("ascii")),
        (b"Content-Type", b"text/plain; charset=utf-8"),
    ]
    if tags:
        headers.append((b"Tags", ",".join(tags).encode("ascii")))
    if click:
        headers.append((b"Click", click.encode("utf-8")))
    if settings.ntfy_token:
        headers.append((b"Authorization", f"Bearer {settings.ntfy_token}".encode("ascii")))

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, content=message.encode("utf-8"), headers=headers)
            if r.status_code != 200:
                print(f"[notify] échec envoi ({r.status_code}) : {r.text[:200]}")
                return False
            return True
    except Exception as e:
        # Journaliser au lieu d'avaler : une alerte perdue en silence est
        # indistinguable d'un système sain pour l'aidant à distance.
        print(f"[notify] échec envoi : {type(e).__name__}: {e}")
        return False


async def notify_screen_disconnected(settings: Settings, recipient_name: str):
    await send_notification(
        settings,
        title=f"⚠️ Snoozolène — Écran déconnecté",
        message=f"L'écran de {recipient_name} s'est déconnecté. Vérifiez la connexion.",
        priority="high",
        tags=["warning"],
    )


async def notify_screen_reconnected(settings: Settings, recipient_name: str):
    await send_notification(
        settings,
        title=f"✅ Snoozolène — Écran reconnecté",
        message=f"L'écran de {recipient_name} est de nouveau en ligne.",
        priority="low",
        tags=["white_check_mark"],
    )


async def notify_screen_boot(settings: Settings, recipient_name: str):
    """Heartbeat de démarrage : premier écran vu depuis le (re)démarrage du
    serveur. L'aidant sait ainsi chaque matin que le système est revenu après
    le reboot nocturne — sans avoir à aller vérifier sur place."""
    await send_notification(
        settings,
        title=f"🖥️ Snoozolène — Écran en ligne",
        message=f"L'écran de {recipient_name} est en ligne (démarrage du système).",
        priority="low",
        tags=["desktop_computer", "white_check_mark"],
    )


async def notify_daily_reminder(settings: Settings):
    await send_notification(
        settings,
        title="📋 Snoozolène — Rappel quotidien",
        message=settings.daily_reminder_message,
        priority="default",
        tags=["memo"],
    )
