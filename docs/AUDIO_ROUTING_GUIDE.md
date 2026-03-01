# Audio Routing Guide for Bobby

## The Confusion: Input vs Output with BlackHole

### Key Concept: BlackHole is a PIPE

```
App A → [writes TO BlackHole] → BlackHole → [reads FROM BlackHole] → App B
        (BlackHole as OUTPUT)                 (BlackHole as INPUT)
```

One app's OUTPUT becomes another app's INPUT.

---

## Three Scenarios

### 1. Testing with `say` command (HEAR IT + CAPTURE IT)

**Setup: Multi-Output Device**

Steps in Audio MIDI Setup:
1. Click the `+` button → Create Multi-Output Device
2. Check BOTH:
   - ☑️ MacBook Air Speakers
   - ☑️ BlackHole 2ch
3. Set System Output to "Multi-Output Device"

**Result:**
```
`say` → Multi-Output → Speakers (you hear it) ✅
                    → BlackHole → audio_capture.py ✅
```

You hear it AND it gets captured!

---

### 2. Testing with `say` command (CAPTURE ONLY, SILENT)

**Setup: BlackHole as System Output**

In System Settings → Sound → Output: BlackHole 2ch

**Result:**
```
`say` → BlackHole → audio_capture.py ✅
     → Speakers (nothing) ❌
```

Works but you don't hear it.

---

### 3. Testing with Your Microphone (CURRENT SETUP)

**Setup: USE_DEFAULT_MIC = True in audio_capture.py**

**Result:**
```
Your Mic → audio_capture.py → Assembly AI ✅
```

Direct! No BlackHole needed.

---

## For Production (Real Zoom Meetings)

**Setup:**
1. In Zoom Settings → Audio:
   - **Microphone**: MacBook Air Microphone (so others hear you)
   - **Speaker**: BlackHole 2ch (so Zoom outputs to BlackHole)

2. In audio_capture.py:
   - Set `USE_DEFAULT_MIC = False`

3. Your laptop speakers:
   - Set System Output back to Speakers
   - Or create Multi-Output (Speakers + BlackHole) if you want to hear the meeting

**Result:**
```
Zoom Meeting:
  - Other people speaking → Zoom outputs to BlackHole
  - Your mic → Zoom → Other people hear you

BlackHole → audio_capture.py → Assembly AI → Transcript ✅

(You speaking also gets transcribed because Zoom "echo" includes your voice)
```

---

## Quick Reference

| You Want To... | System Output | audio_capture.py Setting |
|----------------|---------------|--------------------------|
| Test with `say` + hear it | Multi-Output Device | `USE_DEFAULT_MIC = False` |
| Test with `say` (silent) | BlackHole 2ch | `USE_DEFAULT_MIC = False` |
| Test with your mic | Doesn't matter | `USE_DEFAULT_MIC = True` ← **CURRENT** |
| Real Zoom meeting | Speakers (to hear meeting) | `USE_DEFAULT_MIC = False` |

---

## Creating Multi-Output Device (Recommended for Testing)

1. Open **Audio MIDI Setup**
2. Click **+** (bottom left) → **Create Multi-Output Device**
3. In the Multi-Output settings, check:
   - ☑️ BlackHole 2ch
   - ☑️ MacBook Air Speakers
4. Right-click Multi-Output Device → "Use This Device For Sound Output"
5. In System Settings → Sound → Output: Select "Multi-Output Device"

Now when you run `say`, you'll both HEAR it and CAPTURE it!

---

## Why BlackHole Needs BOTH Input and Output

**BlackHole as OUTPUT only (pointless):**
```
App → BlackHole → [nobody listening] → audio lost ❌
```

**BlackHole as INPUT only (broken):**
```
[nobody talking] → BlackHole → App gets silence ❌
```

**BlackHole correctly used (works!):**
```
App A → BlackHole → App B ✅
(output)         (input)
```

Think of it as a telephone line - needs someone talking AND someone listening!

---

## Troubleshooting

**"I don't hear anything"**
→ System output is set to BlackHole (virtual device)
→ Change to Speakers or Multi-Output Device

**"Audio not being captured"**
→ Check if anything is OUTPUTTING to BlackHole
→ Use Multi-Output Device OR set `USE_DEFAULT_MIC = True`

**"Works with `say` but not my voice"**
→ Microphone is separate from BlackHole
→ Set `USE_DEFAULT_MIC = True` to use mic directly
