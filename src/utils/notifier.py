"""
src/utils/notifier.py

Mobile notification dispatcher for NopeRi.
Sends instant push notifications to your mobile phone when daily applications complete.

Supported notification channels (configured in .env):
1. Telegram Bot (TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID)
2. ntfy.sh Push Notifications (NTFY_TOPIC - zero configuration, free app)
3. Discord Webhook (DISCORD_WEBHOOK_URL)
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from colorama import Fore, Style

logger = logging.getLogger(__name__)

def send_mobile_notification(
    applied_count: int,
    total_found: int,
    skipped_ext: int = 0,
    failed_count: int = 0,
    top_jobs: Optional[list] = None
) -> bool:
    """
    Dispatches a push notification to your phone via any configured channel.
    Returns True if at least one notification was successfully delivered.
    """
    now_str = datetime.now().strftime("%I:%M %p")
    title = f"NopeRi: {applied_count} Jobs Applied!"
    
    # Construct clean message body
    lines = [
        f"Daily Naukri Automation Completed ({now_str})",
        f"- Applied: {applied_count} jobs",
        f"- Unique Fetched: {total_found} jobs",
    ]
    if skipped_ext > 0:
        lines.append(f"- External Apply: {skipped_ext} skipped")
    if failed_count > 0:
        lines.append(f"- Failed: {failed_count}")
        
    lines.append("- Google Sheet: Synced in real-time")

    if top_jobs:
        lines.append("\nApplied To:")
        for j in top_jobs[:5]:
            job_title = j.get("title") or getattr(j, "title", "Role")
            company = j.get("company") or getattr(j, "company", "Company")
            score = j.get("score") or getattr(j, "score", None)
            score_str = f" ({score}/100)" if score else ""
            lines.append(f"  • {job_title} @ {company}{score_str}")

    message_text = "\n".join(lines)
    delivered = False

    # Channel 1: Telegram Bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        try:
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            tg_payload = {
                "chat_id": chat_id,
                "text": f"*{title}*\n\n" + message_text,
                "parse_mode": "Markdown"
            }
            resp = requests.post(tg_url, json=tg_payload, timeout=10)
            if resp.status_code == 200:
                print(f"  {Fore.GREEN}[NOTIFICATION]{Style.RESET_ALL} Telegram mobile alert sent!")
                delivered = True
            else:
                logger.warning(f"Telegram alert failed: {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram dispatch error: {e}")

    # Channel 2: ntfy.sh (Zero login, instant phone push)
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if ntfy_topic:
        try:
            ntfy_url = f"https://ntfy.sh/{ntfy_topic}"
            headers = {
                "Title": title,
                "Priority": "high",
                "Tags": "briefcase,white_check_mark",
            }
            resp = requests.post(ntfy_url, data=message_text.encode("utf-8"), headers=headers, timeout=10)
            if resp.status_code == 200:
                print(f"  {Fore.GREEN}[NOTIFICATION]{Style.RESET_ALL} ntfy push notification sent to mobile!")
                delivered = True
            else:
                logger.warning(f"ntfy alert failed: {resp.text}")
        except Exception as e:
            logger.warning(f"ntfy dispatch error: {e}")

    # Channel 3: Discord Webhook
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_url:
        try:
            discord_payload = {
                "content": f"**{title}**\n```\n{message_text}\n```"
            }
            resp = requests.post(discord_url, json=discord_payload, timeout=10)
            if resp.status_code in (200, 204):
                print(f"  {Fore.GREEN}[NOTIFICATION]{Style.RESET_ALL} Discord mobile alert sent!")
                delivered = True
        except Exception as e:
            logger.warning(f"Discord dispatch error: {e}")

    return delivered
