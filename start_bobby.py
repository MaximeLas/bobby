#!/usr/bin/env python3
"""
Bobby - Python Launcher
Runs all 3 components with colored, labeled output in a single terminal
"""

import subprocess
import sys
import threading
import queue
import time
import os
from pathlib import Path
from datetime import datetime

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

# ANSI color codes
class Colors:
    # Component colors
    AUDIO = '\033[96m'      # Cyan
    ORCHESTRATOR = '\033[93m'  # Yellow
    PROGRESS = '\033[92m'   # Green

    # Status colors
    ERROR = '\033[91m'      # Red
    WARNING = '\033[95m'    # Magenta
    RESET = '\033[0m'       # Reset
    BOLD = '\033[1m'        # Bold
    DIM = '\033[2m'         # Dim

# Component configuration
COMPONENTS = [
    {
        'name': 'AUDIO',
        'label': 'Audio Capture',
        'color': Colors.AUDIO,
        'cmd': ['uv', 'run', 'python3', '-m', 'bobby.audio_capture'],
        'cwd': str(SCRIPT_DIR),
    },
    {
        'name': 'ORCH',
        'label': 'Orchestrator',
        'color': Colors.ORCHESTRATOR,
        'cmd': ['uv', 'run', 'python3', '-m', 'bobby.orchestrator'],  # Will add --test-voice flag if needed
        'cwd': str(SCRIPT_DIR),
    },
    {
        'name': 'WATCH',
        'label': 'Progress Watcher',
        'color': Colors.PROGRESS,
        'cmd': ['uv', 'run', 'python3', '-m', 'bobby.progress_watcher'],
        'cwd': str(SCRIPT_DIR),
    }
]


def timestamp():
    """Get current timestamp"""
    return datetime.now().strftime("%H:%M:%S")


def print_banner(test_voice_only=False):
    """Print startup banner"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    if test_voice_only:
        print(f"{Colors.BOLD}🎤  Bobby - VOICE TEST MODE (No Agent Execution){Colors.RESET}")
    else:
        print(f"{Colors.BOLD}🤖  Bobby - AI Meeting Assistant{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    print(f"{Colors.DIM}Components:{Colors.RESET}")
    for comp in COMPONENTS:
        print(f"  {comp['color']}●{Colors.RESET} {comp['label']} ({comp['name']})")

    print(f"\n{Colors.DIM}Press Ctrl+C to stop all components{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    time.sleep(1)


def stream_output(process, component, output_queue):
    """Read process output line by line and add to queue"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                output_queue.put((component, line.rstrip()))
        process.stdout.close()
    except Exception as e:
        output_queue.put((component, f"ERROR reading output: {e}"))


def print_output(component, line):
    """Print a line with component label and color"""
    color = component['color']
    name = component['name']
    ts = timestamp()

    # Detect error lines
    line_lower = line.lower()
    if 'error' in line_lower or 'exception' in line_lower:
        line_color = Colors.ERROR
    elif 'warning' in line_lower:
        line_color = Colors.WARNING
    else:
        line_color = Colors.RESET

    # Format: [HH:MM:SS] [LABEL] message
    print(f"{Colors.DIM}[{ts}]{Colors.RESET} {color}[{name:5}]{Colors.RESET} {line_color}{line}{Colors.RESET}")
    sys.stdout.flush()


def run_component(component, output_queue):
    """Run a single component process"""
    try:
        # Start process with unbuffered output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output

        process = subprocess.Popen(
            component['cmd'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=component.get('cwd'),
            env=env,
        )

        # Stream output in separate thread
        thread = threading.Thread(
            target=stream_output,
            args=(process, component, output_queue),
            daemon=True
        )
        thread.start()

        return process, thread

    except Exception as e:
        output_queue.put((component, f"FAILED TO START: {e}"))
        return None, None


def main():
    """Main launcher"""
    # Check for --test-voice flag
    test_voice_only = '--test-voice' in sys.argv

    print_banner(test_voice_only)

    # Queue for collecting output from all processes
    output_queue = queue.Queue()

    # Add --test-voice flag to orchestrator if needed
    if test_voice_only:
        for component in COMPONENTS:
            if component['name'] == 'ORCH':
                component['cmd'].append('--test-voice')

    # Start all components
    processes = []
    threads = []

    for component in COMPONENTS:
        color = component['color']
        label = component['label']
        print(f"{color}Starting {label}...{Colors.RESET}")

        process, thread = run_component(component, output_queue)

        if process:
            processes.append((component, process))
            if thread:
                threads.append(thread)
            print(f"{color}✓ {label} started{Colors.RESET}")
        else:
            print(f"{Colors.ERROR}✗ {label} failed to start{Colors.RESET}")

        time.sleep(0.5)

    print(f"\n{Colors.BOLD}All components running!{Colors.RESET}\n")

    # Main loop - print output as it arrives
    try:
        while True:
            try:
                # Get output from queue (with timeout to check for Ctrl+C)
                component, line = output_queue.get(timeout=0.1)
                print_output(component, line)
            except queue.Empty:
                # Check if any process has died
                for comp, proc in processes:
                    if proc.poll() is not None:
                        # Process died
                        print(f"\n{Colors.ERROR}[ERROR] {comp['label']} has stopped unexpectedly{Colors.RESET}\n")
                        raise KeyboardInterrupt
                continue

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Stopping all components...{Colors.RESET}\n")

        # Terminate all processes
        for component, process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"{component['color']}✓ {component['label']} stopped{Colors.RESET}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"{Colors.WARNING}⚠ {component['label']} force killed{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}✗ Error stopping {component['label']}: {e}{Colors.RESET}")

        print(f"\n{Colors.BOLD}Bobby stopped successfully{Colors.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
