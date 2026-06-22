#!/usr/bin/env python3
"""
setup_windows_task.py

Registers a Windows Scheduled Task that runs full_pipeline.py
every day at 9:00 AM using the current Python interpreter.

Run once (as Administrator if you want /RL HIGHEST):
    python setup_windows_task.py

To verify:
    schtasks /Query /TN LinkedInLeadBot /FO LIST

To run immediately:
    schtasks /Run /TN LinkedInLeadBot

To remove:
    schtasks /Delete /TN LinkedInLeadBot /F
"""
import subprocess, sys, os

TASK_NAME = "LinkedInLeadBot"
PYTHON    = sys.executable
SCRIPT    = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "full_pipeline.py")
            )
WORK_DIR  = os.path.dirname(SCRIPT)
RUN_TIME  = "09:00"


def main():
    # Use PowerShell's New-ScheduledTask for a more reliable setup
    ps_script = f"""
$action  = New-ScheduledTaskAction `
    -Execute '{PYTHON}' `
    -Argument '"{SCRIPT}"' `
    -WorkingDirectory '{WORK_DIR}'

$trigger = New-ScheduledTaskTrigger -Daily -At '{RUN_TIME}'

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName '{TASK_NAME}' `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force
"""

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", ps_script],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' registered — runs daily at {RUN_TIME}.")
        print(f"  Script : {SCRIPT}")
        print(f"  Python : {PYTHON}")
        print()
        print("To test immediately:")
        print(f"  schtasks /Run /TN {TASK_NAME}")
        print()
        print("To remove:")
        print(f"  schtasks /Delete /TN {TASK_NAME} /F")
    else:
        print("Registration failed:")
        print(result.stdout)
        print(result.stderr)
        print()
        print("Try running this script as Administrator, or use scheduler.py instead.")


if __name__ == "__main__":
    main()
