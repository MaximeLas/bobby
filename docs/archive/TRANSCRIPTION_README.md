# Audio Transcription with Speaker Diarization

This script uses the AssemblyAI Python SDK to transcribe audio files with speaker labels and timestamps.

## Features

- **Speaker Diarization**: Automatically identifies different speakers in the audio
- **Timestamps**: Provides start and end timestamps for each speaker turn
- **Global English**: Configured for Global English language
- **Confidence Scores**: Shows confidence level for each utterance
- **Duration Tracking**: Displays how long each person speaks
- **File Export**: Optionally save results to a text file

## Installation

1. Install the AssemblyAI Python SDK:

```bash
pip install assemblyai
```

2. Get your API key from [AssemblyAI Dashboard](https://www.assemblyai.com/app/api-keys)

3. Set your API key as an environment variable:

```bash
export ASSEMBLYAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Usage

Transcribe a local audio file:

```bash
python transcribe_audio.py ./path/to/audio.mp3
```

Transcribe from a URL:

```bash
python transcribe_audio.py https://example.com/audio.mp3
```

### Save Results to File

```bash
python transcribe_audio.py ./audio.mp3 transcript.txt
```

## Output Format

The script displays results in the following format:

```
================================================================================
TRANSCRIPTION RESULTS
================================================================================

Total speakers detected: 2
Total utterances: 15

================================================================================

[1] Speaker A
    Time: 00:00:00.250 --> 00:00:26.950 (Duration: 00:00:26.700)
    Confidence: 93.59%
    Text: Smoke from hundreds of wildfires in Canada is triggering...

[2] Speaker B
    Time: 00:00:27.850 --> 00:00:28.840 (Duration: 00:00:00.990)
    Confidence: 99.30%
    Text: Good morning.
```

## What You Get

For each speaker turn, the script provides:

- **Speaker Label**: Letter identifier (A, B, C, etc.)
- **Start Time**: When the speaker starts talking (HH:MM:SS.mmm)
- **End Time**: When the speaker stops talking (HH:MM:SS.mmm)
- **Duration**: How long the speaker talks
- **Confidence**: Transcription confidence score (0-100%)
- **Text**: What the speaker said

## Supported Audio Formats

AssemblyAI supports a wide range of audio and video formats including:
- MP3, MP4, WAV, FLAC, AAC
- M4A, OGG, WebM
- And many more

See [AssemblyAI FAQ](https://www.assemblyai.com/docs/faq) for the complete list.

## Notes

- The script only provides timestamps for **speaker turns** (when a new speaker starts talking), not for individual words or sentences
- Timestamps are in milliseconds precision
- Speaker labels are automatically assigned as A, B, C, etc.
- For best results, ensure each speaker speaks for at least 30 seconds uninterrupted
- The script is configured for Global English (`en`) but can be modified for other languages

## Customization

To change the language, modify the `language` parameter in the script:

```python
transcript = transcribe_with_diarization(
    audio_file_path=audio_file,
    api_key=api_key,
    language="en"  # Change to other language codes like "es", "fr", "de", etc.
)
```

Supported languages for speaker diarization include: English (en, en_us, en_uk, en_au), Spanish (es), French (fr), German (de), Italian (it), Portuguese (pt), and many more.

## Troubleshooting

**API Key Not Found**
- Make sure you've set the `ASSEMBLYAI_API_KEY` environment variable
- Alternatively, you can modify the script to use a hardcoded API key (not recommended for production)

**Transcription Failed**
- Check that your audio file is accessible and in a supported format
- Verify your API key is valid
- Check your internet connection

**Poor Diarization Results**
- Ensure each speaker speaks for at least 30 seconds
- Avoid cross-talk or overlapping speech
- Use good quality audio with minimal background noise

## Example

```bash
# Set your API key (do this once per session)
export ASSEMBLYAI_API_KEY="your-api-key-here"

# Transcribe a local file
python transcribe_audio.py ./meeting_recording.mp3

# Transcribe and save to file
python transcribe_audio.py ./interview.mp3 interview_transcript.txt
```
