"""
setup_daily_schedule.py

Utility to schedule Naukri Automation Agent in Windows Task Scheduler.
This allows the agent to automatically run every morning, refresh your
Naukri profile ("Active Today"), apply to jobs, and sync to Google Sheets.

Usage:
    python setup_daily_schedule.py --install [time]    # e.g. 09:00 (default: 09:00 AM)
    python setup_daily_schedule.py --uninstall
    python setup_daily_schedule.py --status
    python setup_daily_schedule.py --run-now
"""

import os
import sys
import subprocess
import argparse
from colorama import Fore, Style, init

init(autoreset=True)

TASK_NAME = "Naukri_Daily_Automation"

def get_python_executable(windowless=True):
    exe_name = "pythonw.exe" if windowless else "python.exe"
    venv_py = os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv", "Scripts", exe_name))
    if os.path.exists(venv_py):
        return venv_py
    return sys.executable

def install_task(time_str="09:00"):
    python_exe = get_python_executable(windowless=True)
    runner_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "daily_runner.py"))
    working_dir = os.path.abspath(os.path.dirname(__file__))

    print(f"\n{Fore.CYAN}Installing Windows Scheduled Task '{TASK_NAME}'...{Style.RESET_ALL}")
    print(f"  Python       : {python_exe} (Windowless / Silent Background)")
    print(f"  Script       : {runner_script}")
    print(f"  Schedule     : Daily at {Fore.GREEN}{time_str}{Style.RESET_ALL}")
    print(f"  Missed Start : {Fore.GREEN}Starts immediately whenever laptop is opened / unlocked{Style.RESET_ALL}")
    print(f"  Power Mode   : {Fore.GREEN}Allowed on both Battery and AC Power{Style.RESET_ALL}")

    try:
        # Step 1: Create the base task with clean unquoted binary and script arguments
        cmd_create = [
            "schtasks", "/create",
            "/tn", TASK_NAME,
            "/tr", f"{python_exe} {runner_script}",
            "/sc", "daily",
            "/st", time_str,
            "/f"
        ]
        res = subprocess.run(cmd_create, capture_output=True, text=True)

        if res.returncode == 0:
            # Step 2: Configure Smart Catch-Up (StartWhenAvailable) and Battery Execution
            ps_settings = (
                f'$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; '
                f'Set-ScheduledTask -TaskName "{TASK_NAME}" -Settings $s'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_settings], capture_output=True, text=True)

            print(f"\n{Fore.GREEN}SUCCESS! Task '{TASK_NAME}' registered with Smart Catch-Up.{Style.RESET_ALL}")
            print(f"-> Runs daily at {time_str}.")
            print(f"-> StartWhenAvailable: YES (runs automatically if laptop was asleep/closed)")
            print(f"-> Battery Mode: ALLOWED (runs on both battery and AC power)")
            print(f"To test immediately, run: {Fore.YELLOW}python setup_daily_schedule.py --run-now{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to create task:{Style.RESET_ALL}\n{res.stderr or res.stdout}")
    except Exception as e:
        print(f"{Fore.RED}Error registering task: {e}{Style.RESET_ALL}")

def uninstall_task():
    print(f"\n{Fore.CYAN}Removing Windows Scheduled Task '{TASK_NAME}'...{Style.RESET_ALL}")
    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{Fore.GREEN}Task '{TASK_NAME}' successfully removed.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}{res.stderr.strip() or res.stdout.strip()}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

def check_status():
    print(f"\n{Fore.CYAN}Checking status for '{TASK_NAME}'...{Style.RESET_ALL}")
    cmd = ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST", "/v"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{Fore.GREEN}Task is ACTIVE:{Style.RESET_ALL}\n")
            for line in res.stdout.splitlines():
                if any(k in line for k in ["TaskName", "Next Run Time", "Status", "Schedule Type", "Start Time"]):
                    print(f"  {line}")
        else:
            print(f"{Fore.YELLOW}Task '{TASK_NAME}' is NOT registered yet.{Style.RESET_ALL}")
            print(f"Run {Fore.CYAN}python setup_daily_schedule.py --install 09:00{Style.RESET_ALL} to enable it.")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

def run_now():
    print(f"\n{Fore.CYAN}Triggering task '{TASK_NAME}' right now...{Style.RESET_ALL}")
    cmd = ["schtasks", "/run", "/tn", TASK_NAME]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"{Fore.GREEN}Task triggered successfully! Check daily_runs.log for logs.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed: {res.stderr or res.stdout}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Naukri Automation Agent Windows Scheduler Setup")
    parser.add_argument("--install", nargs="?", const="09:00", help="Install daily task (e.g. 09:00 or 10:30)")
    parser.add_argument("--uninstall", action="store_true", help="Remove the daily task")
    parser.add_argument("--status", action="store_true", help="Check task status")
    parser.add_argument("--run-now", action="store_true", help="Trigger task immediately")

    args = parser.parse_args()

    if args.uninstall:
        uninstall_task()
    elif args.status:
        check_status()
    elif args.run_now:
        run_now()
    elif args.install:
        install_task(args.install)
    else:
        # Default interactive menu
        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"  {Style.BRIGHT}Naukri Automation Agent Daily Scheduler{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print("  1. Install / Schedule Daily Task (Default 09:00 AM)")
        print("  2. Check Status")
        print("  3. Run Now")
        print("  4. Remove / Uninstall Task")
        print("  0. Exit")
        choice = input("\nSelect an option [1-4]: ").strip()
        if choice == "1":
            t = input("Enter daily run time (HH:MM in 24hr format, default 09:00): ").strip() or "09:00"
            install_task(t)
        elif choice == "2":
            check_status()
        elif choice == "3":
            run_now()
        elif choice == "4":
            uninstall_task()

if __name__ == "__main__":
    main()
