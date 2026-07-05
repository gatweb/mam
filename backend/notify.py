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
    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if click:
        headers["Click"] = click
    if settings.ntfy_token:
        headers["Authorization"] = f"Bearer {settings.ntfy_token}"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, content=message.encode("utf-8"), headers=headers)
            return r.status_code == 200
    except Exception:
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


async def notify_daily_reminder(settings: Settings):
    await send_notification(
        settings,
        title="📋 Snoozolène — Rappel quotidien",
        message=settings.daily_reminder_message,
        priority="default",
        tags=["memo"],
    )
