#!/usr/bin/env python3
"""
Bobby Progress Watcher - Component 3

Watches agent_progress.txt and displays updates with:
1. Rich terminal UI with colors and formatting
2. macOS notifications for every update

Author: Claude
Date: 2025-10-25
"""

import time
import os
import subprocess
import signal
import sys
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Warning: 'rich' library not installed. Install with: pip install rich")
    print("   Falling back to basic color output...\n")


from bobby.config import PROGRESS_FILE
POLL_INTERVAL = 0.5  # seconds - fast enough for real-time feel


class ProgressWatcher:
    """Watches agent_progress.txt and displays updates"""

    def __init__(self, progress_file=PROGRESS_FILE):
        self.progress_file = progress_file
        self.running = True
        self.console = Console() if RICH_AVAILABLE else None

        # Seek to END of file so we only process NEW updates (like orchestrator does)
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                f.seek(0, 2)  # Seek to end
                self.last_position = f.tell()
        else:
            self.last_position = 0

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n")
        if RICH_AVAILABLE:
            self.console.print("\n[yellow]👋 Progress watcher stopped[/yellow]")
        else:
            print("👋 Progress watcher stopped")
        self.running = False
        sys.exit(0)

    def send_notification(self, title, message):
        """
        Send macOS notification using terminal-notifier

        Args:
            title: Notification title
            message: Notification message
        """
        try:
            # Clean message for terminal-notifier (it fails with special chars at start)
            # Remove emojis and ASCII arrow prefix
            import re
            clean_message = re.sub(r'[🔍✅❌→➡️⚠️📢🎯✓]', '', message).strip()
            # Remove ASCII arrow at start (e.g., "-> Starting task" becomes "Starting task")
            if clean_message.startswith('->'):
                clean_message = clean_message[2:].strip()

            # Build terminal-notifier command
            # Use UUID for group ID to guarantee uniqueness (timestamp can collide if agent writes fast)
            import uuid
            unique_group = f'bobby-{uuid.uuid4()}'

            cmd = [
                'terminal-notifier',
                '-title', title,
                '-message', clean_message,
                '-sender', 'com.apple.Terminal',  # Shows as Terminal in notifications
                '-group', unique_group  # Unique group per notification so they stack
            ]

            # Add sound for questions
            if 'question' in title.lower():
                cmd.extend(['-sound', 'default'])

            # Execute terminal-notifier
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                check=False
            )

            # Log any errors (for debugging) - show FULL error
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8') if result.stderr else ''
                stdout = result.stdout.decode('utf-8') if result.stdout else ''
                print(f"⚠️  terminal-notifier failed (code {result.returncode})")
                print(f"    Command: {' '.join(cmd)}")
                print(f"    Message being sent: {repr(clean_message)}")
                if stderr:
                    print(f"    Stderr: {stderr}")
                if stdout:
                    print(f"    Stdout (first 200 chars): {stdout[:200]}")

            # Log notification sent
            if RICH_AVAILABLE:
                self.console.print(f"[dim]   📢 Notification sent: {title}[/dim]")

        except FileNotFoundError:
            print("⚠️  terminal-notifier not found. Install with: brew install terminal-notifier")
        except subprocess.TimeoutExpired:
            print(f"⚠️  Notification timed out: {title}")
        except Exception as e:
            print(f"⚠️  Notification error: {e}")

    def display_update(self, line):
        """
        Display update in terminal with colors and send notification

        Args:
            line: Progress line from agent_progress.txt
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Determine update type and parse message
        if line.startswith('PROGRESS:'):
            update_type = 'PROGRESS'
            message = line.replace('PROGRESS:', '').strip()
            self._display_progress(timestamp, message)
            self.send_notification("Bobby Progress", message)

        elif line.startswith('QUESTION:'):
            update_type = 'QUESTION'
            message = line.replace('QUESTION:', '').strip()
            self._display_question(timestamp, message)
            self.send_notification("Bobby Question", message)

        elif line.startswith('COMPLETE:'):
            update_type = 'COMPLETE'
            message = line.replace('COMPLETE:', '').strip()
            self._display_complete(timestamp, message)
            self.send_notification("Bobby Complete", message)

        elif line.startswith('ERROR:'):
            update_type = 'ERROR'
            message = line.replace('ERROR:', '').strip()
            self._display_error(timestamp, message)
            self.send_notification("Bobby Error", message)

        else:
            # Unknown format - display as-is
            self._display_unknown(timestamp, line)

    def _display_progress(self, timestamp, message):
        """Display PROGRESS update"""
        if RICH_AVAILABLE:
            # Check if it's a completion mark (contains ✓)
            if '✓' in message or message.strip().startswith('✓'):
                # Completed step - green
                self.console.print(f"[dim][{timestamp}][/dim] [green]✅  {message}[/green]")
            else:
                # In-progress step - cyan
                self.console.print(f"[dim][{timestamp}][/dim] [cyan]🔍 {message}[/cyan]")
        else:
            print(f"[{timestamp}] 🔍 {message}")

    def _display_question(self, timestamp, message):
        """Display QUESTION update"""
        if RICH_AVAILABLE:
            self.console.print(f"[dim][{timestamp}][/dim] [yellow bold]❓ QUESTION: {message}[/yellow bold]")
        else:
            print(f"[{timestamp}] ❓ QUESTION: {message}")

    def _display_complete(self, timestamp, message):
        """Display COMPLETE update"""
        if RICH_AVAILABLE:
            self.console.print(f"[dim][{timestamp}][/dim] [green bold]✅ COMPLETE: {message}[/green bold]")
        else:
            print(f"[{timestamp}] ✅ COMPLETE: {message}")

    def _display_error(self, timestamp, message):
        """Display ERROR update"""
        if RICH_AVAILABLE:
            self.console.print(f"[dim][{timestamp}][/dim] [red bold]❌ ERROR: {message}[/red bold]")
        else:
            print(f"[{timestamp}] ❌ ERROR: {message}")

    def _display_unknown(self, timestamp, line):
        """Display unknown format"""
        if RICH_AVAILABLE:
            self.console.print(f"[dim][{timestamp}][/dim] {line}")
        else:
            print(f"[{timestamp}] {line}")

    def show_banner(self):
        """Display startup banner"""
        if RICH_AVAILABLE:
            banner_text = Text()
            banner_text.append("🤖 Bobby Progress Watcher\n", style="bold cyan")
            banner_text.append(f"Watching: {self.progress_file}\n", style="dim")
            banner_text.append("Notifications: Enabled\n", style="green")
            banner_text.append("Press Ctrl+C to stop", style="yellow")

            panel = Panel(
                banner_text,
                border_style="cyan",
                width=60
            )
            self.console.print(panel)
            self.console.print()
        else:
            print("🤖 Bobby Progress Watcher")
            print("━" * 60)
            print(f"Watching: {self.progress_file}")
            print("Notifications: Enabled")
            print("Press Ctrl+C to stop")
            print("━" * 60)
            print()

    def watch(self):
        """Main watch loop - continuously monitor progress file"""
        self.show_banner()

        if RICH_AVAILABLE:
            self.console.print("[dim]⏳ Waiting for progress updates...[/dim]\n")
        else:
            print("⏳ Waiting for progress updates...\n")

        while self.running:
            try:
                # Check if file exists
                if not os.path.exists(self.progress_file):
                    time.sleep(POLL_INTERVAL)
                    continue

                # Read new content
                with open(self.progress_file, 'r') as f:
                    # Check if file was cleared (size < last_position)
                    # This happens when the agent clears the file itself
                    f.seek(0, 2)  # Seek to end to get file size
                    file_size = f.tell()

                    if file_size < self.last_position:
                        # File was cleared! Reset to beginning
                        self.last_position = 0

                    # Seek to last position
                    f.seek(self.last_position)

                    # Read new content
                    new_content = f.read()

                    # Update position
                    self.last_position = f.tell()

                # Process new content
                if new_content:
                    lines = new_content.strip().split('\n')
                    for line in lines:
                        if line.strip():  # Skip empty lines
                            self.display_update(line)
                            # Small delay to prevent macOS notification throttling
                            time.sleep(0.3)

                # Sleep before next poll
                time.sleep(POLL_INTERVAL)

            except FileNotFoundError:
                # File was deleted - reset position
                self.last_position = 0
                time.sleep(POLL_INTERVAL)

            except IOError as e:
                print(f"⚠️  File I/O error: {e}")
                time.sleep(POLL_INTERVAL)

            except Exception as e:
                print(f"⚠️  Unexpected error: {e}")
                time.sleep(POLL_INTERVAL)


def main():
    """Entry point"""
    watcher = ProgressWatcher()
    watcher.watch()


if __name__ == "__main__":
    main()
