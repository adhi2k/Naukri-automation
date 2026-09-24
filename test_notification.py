"""
test_notification.py

Test utility to send an instant test push notification to your mobile phone.
Usage:
    python test_notification.py
"""

import os
from dotenv import load_dotenv
from colorama import Fore, Style, init

load_dotenv(override=True)
init(autoreset=True)

from src.utils.notifier import send_mobile_notification

def main():
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}Testing NopeRi Mobile Notification Dispatcher{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    ntfy_topic = os.getenv("NTFY_TOPIC")
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")

    active_channels = []
    if tg_token and tg_chat:
        active_channels.append("Telegram Bot")
    if ntfy_topic:
        active_channels.append(f"ntfy.sh (Topic: {ntfy_topic})")
    if discord_url:
        active_channels.append("Discord Webhook")

    if not active_channels:
        print(f"  {Fore.YELLOW}No mobile notification channel configured in .env!{Style.RESET_ALL}\n")
        print("  Choose one of these easy options:")
        print(f"  {Style.BRIGHT}Option 1: ntfy.sh (Zero Setup - Takes 30 seconds){Style.RESET_ALL}")
        print("    1. Install the free 'ntfy' app from Google Play Store or App Store on your phone.")
        print("    2. Open app -> Click '+' -> Subscribe to any unique topic name (e.g. 'noperi_adhithya_jobs').")
        print("    3. Add to your .env:")
        print(f"       {Fore.GREEN}NTFY_TOPIC=noperi_adhithya_jobs{Style.RESET_ALL}\n")
        print(f"  {Style.BRIGHT}Option 2: Telegram Bot{Style.RESET_ALL}")
        print("    1. Open Telegram -> Message @BotFather -> create bot -> get Bot Token.")
        print("    2. Message @userinfobot -> get your Chat ID.")
        print("    3. Add to your .env:")
        print(f"       {Fore.GREEN}TELEGRAM_BOT_TOKEN=...{Style.RESET_ALL}")
        print(f"       {Fore.GREEN}TELEGRAM_CHAT_ID=...{Style.RESET_ALL}\n")
        return

    print(f"  Configured channels: {Fore.GREEN}{', '.join(active_channels)}{Style.RESET_ALL}")
    print("  Sending test push notification now...")

    dummy_jobs = [
        {"title": "Python Developer", "company": "Ziroh Labs", "score": 85},
        {"title": "FastAPI / AI Engineer", "company": "Tech Innovations", "score": 92},
    ]

    success = send_mobile_notification(
        applied_count=20,
        total_found=65,
        skipped_ext=2,
        failed_count=0,
        top_jobs=dummy_jobs
    )

    if success:
        print(f"\n{Fore.GREEN}SUCCESS! Check your mobile phone for the notification.{Style.RESET_ALL}\n")
    else:
        print(f"\n{Fore.RED}Notification failed. Please verify your credentials in .env.{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
