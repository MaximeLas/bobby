# tmux Quick Reference for Bobby

## Starting Bobby

```bash
./start_bobby.sh
```

This launches 3 panes:

- **Top-left**: Audio Capture (Assembly AI streaming)
- **Top-right**: Orchestrator (Trigger detection)
- **Bottom**: Progress Watcher (Bobby's updates)

## Stopping Bobby

**Option 1: From outside tmux**

```bash
./stop_bobby.sh
```

**Option 2: From inside tmux**
Press `Ctrl+C` in each pane to stop the scripts

## tmux Basics

### The Magic Prefix: `Ctrl+b`

Almost all tmux commands start with pressing `Ctrl+b`, then releasing, then pressing another key.

### Essential Commands

| Command                    | What it does                                    |
| -------------------------- | ----------------------------------------------- |
| `Ctrl+b` then `←/→/↑/↓`    | **Navigate between panes** (most important!)    |
| `Ctrl+b` then `d`          | **Detach** (Bobby keeps running in background)  |
| `Ctrl+b` then `x` then `y` | **Kill current pane**                           |
| `Ctrl+b` then `[`          | **Scroll mode** (use arrow keys, `q` to exit)   |
| `Ctrl+b` then `z`          | **Zoom pane** (fullscreen toggle)               |
| `Ctrl+c`                   | **Stop script** in current pane (normal Ctrl+c) |

### Scrolling & Copy-Paste (IMPORTANT!)

**To scroll up and see old output:**

1. Press `Ctrl+b` then `[` (enters "copy mode")
2. Use arrow keys, Page Up/Down, or mouse wheel to scroll
3. Press `q` to exit copy mode

**To copy text:**

1. Press `Ctrl+b` then `[` (enters copy mode)
2. Navigate to the start of text you want
3. Press `Space` to start selection
4. Move cursor to end of text (it highlights)
5. Press `Enter` to copy
6. Press `q` to exit copy mode
7. To paste: `Ctrl+b` then `]`

**To copy to system clipboard (for pasting outside tmux):**

- After selecting text (steps 1-4 above), press `Enter`
- Then use your terminal's "Edit → Copy" or mouse right-click → Copy
- Or enable mouse mode (see below)

**Enable mouse support (easier scrolling/copying):**

1. Run: `echo "set -g mouse on" >> ~/.tmux.conf`
2. Restart tmux or run: `tmux source-file ~/.tmux.conf`
3. Now you can:
   - Scroll with mouse wheel
   - Click to switch panes
   - Click and drag to select text (auto-copies to tmux buffer)

### Typical Workflow

1. **Start Bobby**: `./start_bobby.sh`

   - You're now inside tmux with 3 panes running

2. **Switch panes to check output**:

   - Press `Ctrl+b` then `→` to go to Orchestrator
   - Press `Ctrl+b` then `↓` to go to Progress Watcher
   - Press `Ctrl+b` then `←` to go back to Audio Capture

3. **Scroll up to see old output**:

   - Press `Ctrl+b` then `[`
   - Use arrow keys or Page Up/Down to scroll
   - Press `q` to exit scroll mode

4. **Zoom a pane** (make it fullscreen temporarily):

   - Press `Ctrl+b` then `z`
   - Press again to unzoom

5. **Detach and keep Bobby running**:

   - Press `Ctrl+b` then `d`
   - Bobby continues in background
   - Reattach anytime with: `tmux attach -t bobby`

6. **Stop everything**:
   - Either run `./stop_bobby.sh` from outside tmux
   - Or press `Ctrl+c` in each pane

## Troubleshooting

**"Session bobby already exists"**

- Run `./stop_bobby.sh` first
- Or manually: `tmux kill-session -t bobby`

**Can't see some output**

- Enter scroll mode: `Ctrl+b` then `[`
- Scroll up with arrow keys
- Press `q` to exit

**Accidentally closed a pane**

- Just restart Bobby: `./stop_bobby.sh` then `./start_bobby.sh`

**Want to run commands in a pane**

- `Ctrl+c` to stop the current script
- Type your command
- Re-run the script when done

## Advanced Tips

**Copy text from tmux**:

1. `Ctrl+b` then `[` (scroll mode)
2. Move to start of text
3. Press `Space` to start selection
4. Move to end of text
5. Press `Enter` to copy
6. Paste with: `Ctrl+b` then `]`

**See all tmux sessions**:

```bash
tmux ls
```

**Attach to Bobby if detached**:

```bash
tmux attach -t bobby
```

**Create a new window** (like a new tab):

- `Ctrl+b` then `c`
- Switch windows: `Ctrl+b` then `0-9`

## Why tmux is Awesome

- **Persistent**: SSH disconnects won't kill your processes
- **Multi-pane**: See multiple things at once
- **Detachable**: Start work, detach, go home, reattach later
- **Shareable**: Multiple people can attach to same session

You'll find yourself using tmux for everything once you get the hang of it!

---

**Main thing to remember**: Almost everything is `Ctrl+b` then another key.
