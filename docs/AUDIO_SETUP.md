# Audio Capture Setup Guide

This guide will help you set up Bobby's audio capture component for real-time meeting transcription.

## Prerequisites

- macOS (BlackHole is macOS-only)
- Python 3.12 or higher
- Homebrew (for installing BlackHole)
- Assembly AI API key

## Step 1: Install BlackHole

BlackHole is a virtual audio device that allows you to route audio from one application to another.

```bash
# Install BlackHole 2ch (2-channel version)
brew install blackhole-2ch

# Verify installation
brew list | grep blackhole
```

## Step 2: Configure Audio MIDI Setup

You need to create a Multi-Output Device to route audio to both your speakers and BlackHole.

### 2.1 Open Audio MIDI Setup

1. Open **Applications > Utilities > Audio MIDI Setup**
2. Or use Spotlight: Press `Cmd+Space` and type "Audio MIDI Setup"

### 2.2 Create Multi-Output Device

1. Click the **+** button in the bottom-left corner
2. Select **Create Multi-Output Device**
3. Name it something like "BlackHole + Speakers"
4. Check the boxes for:
   - **BlackHole 2ch** (this is what Bobby will listen to)
   - **Your built-in speakers or headphones** (so you can still hear audio)

### 2.3 Create Aggregate Device (Optional but Recommended)

This allows better control over audio routing:

1. Click the **+** button again
2. Select **Create Aggregate Device**
3. Name it "Meeting Audio"
4. Check the boxes for:
   - **BlackHole 2ch**
   - **Your built-in microphone** (if you want to capture your own voice too)

### 2.4 Set System Audio Output

1. Go to **System Settings > Sound**
2. Under **Output**, select your "BlackHole + Speakers" device
3. This routes all system audio to both BlackHole and your speakers

## Step 3: Install Python Dependencies

```bash
# Navigate to project directory
cd ~/Projects/bobby

# Install dependencies
uv sync
```

### Troubleshooting PyAudio Installation

If `uv sync` fails on PyAudio, install PortAudio first:

```bash
brew install portaudio
uv sync
```

## Step 4: Configure Assembly AI API Key

### 4.1 Get Your API Key

1. Sign up or log in at https://www.assemblyai.com
2. Go to https://www.assemblyai.com/app/api-keys
3. Copy your API key

### 4.2 Create .env File

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# Replace 'your_api_key_here' with your actual API key
```

Your `.env` file should look like:
```
ASSEMBLYAI_API_KEY=abc123yourrealapikey456def
```

## Step 5: Test the Setup

### 5.1 Run Audio Capture

```bash
uv run python3 -m bobby.audio_capture
```

You should see output like:
```
============================================================
Bobby Audio Capture - Component 1
============================================================
2025-10-25 14:30:00 - INFO - Searching for BlackHole audio device...
2025-10-25 14:30:00 - INFO - Found BlackHole device: BlackHole 2ch (index: 2)
2025-10-25 14:30:00 - INFO - Audio stream started (sample rate: 16000Hz, chunk size: 1024)
2025-10-25 14:30:00 - INFO - Writing transcripts to: /Users/maximelas/Projects/bobby/sandbox/meeting_transcript.txt
2025-10-25 14:30:00 - INFO - Connecting to Assembly AI streaming service...
2025-10-25 14:30:01 - INFO - Connected to Assembly AI
2025-10-25 14:30:01 - INFO - Starting real-time transcription...
2025-10-25 14:30:01 - INFO - Streaming session started: abc-123-def
2025-10-25 14:30:01 - INFO - Listening for audio... (Press Ctrl+C to stop)
```

### 5.2 Test with Audio

1. With `audio_capture.py` running, play some audio on your Mac:
   - Play a YouTube video
   - Play a podcast
   - Start a Zoom/Meet call
   - Or just speak into your microphone if you set up the Aggregate Device

2. Watch the console for transcription output:
   ```
   2025-10-25 14:31:15 - INFO - TRANSCRIPT: [14:31:15] Speaker A: Hello, this is a test of the audio capture system.
   ```

3. Check the `meeting_transcript.txt` file:
   ```bash
   tail -f meeting_transcript.txt
   ```

   You should see:
   ```
   [14:31:15] === New Recording Session ===

   [14:31:15] Speaker A: Hello, this is a test of the audio capture system.
   ```

### 5.3 Stop the Capture

Press `Ctrl+C` to stop the audio capture gracefully.

## Testing with the Orchestrator

Once audio capture is working, you can test the full Bobby integration:

1. In one terminal, start the audio capture:
   ```bash
   uv run python3 -m bobby.audio_capture
   ```

2. In another terminal, start the orchestrator:
   ```bash
   uv run python3 -m bobby.orchestrator
   ```

3. Say or play audio containing: "Hey Bobby, please build this"

4. The orchestrator should detect the trigger and respond!

## Common Issues

### Issue: BlackHole device not found

**Solution:**
- Verify BlackHole is installed: `brew list | grep blackhole`
- If not installed: `brew install blackhole-2ch`
- Restart your Mac after installation
- Run `uv run python3 -m bobby.audio_capture` again

### Issue: No audio being captured

**Solution:**
1. Check that your system audio output is set to "BlackHole + Speakers" (or your Multi-Output Device)
2. Ensure audio is actually playing on your Mac
3. Check Audio MIDI Setup to verify the Multi-Output Device is configured correctly
4. Try using the Aggregate Device instead

### Issue: PyAudio installation fails

**Solution:**
```bash
brew install portaudio
uv sync
```

### Issue: Assembly AI connection error

**Solution:**
1. Check your internet connection
2. Verify your API key is correct in `.env`
3. Ensure you have Assembly AI credits available
4. Check Assembly AI status: https://status.assemblyai.com

### Issue: Permission denied on audio device

**Solution:**
1. Go to **System Settings > Privacy & Security > Microphone**
2. Enable microphone access for Terminal or your Python IDE

### Issue: Transcripts are delayed or missing

**Solution:**
1. Check your internet connection speed
2. Ensure audio quality is good (no heavy echo/noise)
3. Speak clearly or ensure audio source is clear
4. Assembly AI streaming has ~2-3 second latency (this is normal)

## Audio Routing Diagrams

### For Meeting Audio (Zoom, Google Meet, etc.)

```
Meeting App Audio
       ↓
Multi-Output Device
       ↓
  ┌────┴────┐
  ↓         ↓
BlackHole  Speakers
  ↓         ↓
  Bobby    You Hear It
```

### For Testing with Your Voice

```
Your Microphone
       ↓
Aggregate Device
       ↓
  BlackHole
       ↓
      Bobby
```

## Advanced Configuration

### Adjusting Sample Rate

The default sample rate is 16kHz (16000 Hz), which is optimal for speech recognition. If you need to change it:

1. Edit `bobby/audio_capture.py`
2. Change the `sample_rate` parameter in both:
   - `BlackHoleAudioStream(sample_rate=16000, ...)`
   - `StreamingParameters(sample_rate=16000, ...)`
3. Keep both values identical

### Adjusting Chunk Size

The chunk size affects latency and stability. Default is 1024.

- Smaller chunks = lower latency, higher CPU usage, more prone to dropouts
- Larger chunks = higher latency, lower CPU usage, more stable

To change it, edit the `chunk_size` parameter in `BlackHoleAudioStream`.

## File Structure

```
bobby/
├── bobby/
│   ├── config.py            # Centralized path configuration
│   └── audio_capture.py     # Audio capture module
├── docs/
│   ├── AUDIO_SETUP.md       # This file
│   └── AUDIO_ROUTING_GUIDE.md  # BlackHole routing concepts
├── sandbox/
│   └── meeting_transcript.txt   # Output transcript file (runtime)
├── pyproject.toml           # Python dependencies (managed with uv)
├── .env                     # Your API keys (DO NOT COMMIT)
└── .env.example             # Template for .env
```

## Notes on Speaker Diarization

Assembly AI's streaming v3 API does not yet support speaker diarization (identifying individual speakers). The current implementation labels all speakers as "Speaker A".

For multi-speaker support, you would need to:
1. Use Assembly AI's pre-recorded transcription API (not real-time), or
2. Wait for Assembly AI to add speaker diarization to streaming API, or
3. Use a different transcription service that supports real-time speaker diarization

The code is structured to easily add speaker labels when this feature becomes available.

## Next Steps

After completing this setup:

1. Test that transcripts appear in `meeting_transcript.txt`
2. Verify timestamps are correct
3. Test the trigger phrase: "Hey Bobby, please build this"
4. Integrate with the orchestrator component
5. Set up the code execution component (Component 2)

## Resources

- BlackHole: https://github.com/ExistentialAudio/BlackHole
- Assembly AI Docs: https://www.assemblyai.com/docs
- PyAudio Docs: https://people.csail.mit.edu/hubert/pyaudio/

## Support

If you encounter issues not covered in this guide:

1. Check the Assembly AI documentation
2. Verify your system audio configuration
3. Test BlackHole independently
4. Check Python and dependency versions
