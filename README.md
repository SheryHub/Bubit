# 🎧 Bubit - Real-Time Subtitle Widget

A sleek, floating desktop widget that provides real-time subtitles/captions for any audio playing on your Windows computer. Powered by AssemblyAI's Universal-Streaming speech recognition API.

![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.7+-green?style=flat-square)
![AssemblyAI](https://img.shields.io/badge/AI-AssemblyAI-purple?style=flat-square)

## 📁 Project Structure

```
bubit/
├── run.py              # Main application code (the widget)
├── widget.spec         # PyInstaller spec for building executable
├── version.txt         # Version number for builds
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## ✨ Features

- **🎙️ Real-Time Transcription** - Captures system audio and transcribes it live with ~300ms latency
- **🖥️ Floating Widget** - Minimalist, borderless window that stays on top and can be dragged anywhere
- **📝 Note Taking** - Optional feature to save all transcripts to `note.txt` with timestamps
- **⏱️ Session Management** - 2-minute session timeout to manage API usage costs
- **🎨 Modern UI** - Dark theme with smooth animations and visual feedback
- **🔊 WASAPI Loopback** - Uses Windows Audio Session API to capture "what you hear"
- **📦 Executable Ready** - Includes PyInstaller spec for building standalone `.exe`

## 🤖 How It Works

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  System Audio   │────▶│  WASAPI Loopback   │────▶│  PyAudio Stream   │
│  (Speakers/Apps)│     │  (What You Hear)   │     │  (48kHz, Stereo)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Subtitle Display │◄────│  AssemblyAI API    │◄────│  Audio Processing │
│  (Floating Window)│     │  (WebSocket v3)    │     │  (Resample to 16kHz)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### AI Technology: AssemblyAI Universal-Streaming

- **Model**: `universal-streaming-english`
- **Latency**: ~300ms (P50)
- **Protocol**: WebSocket streaming at `wss://streaming.assemblyai.com/v3/ws`
- **Audio Format**: PCM 16-bit, 16kHz (resampled from 48kHz system audio)
- **Pricing**: $0.15/hour (free tier: 333 hours/month)

The widget uses **WASAPI loopback recording** via `pyaudiowpatch` to capture whatever is playing through your speakers/headphones. It processes the audio (converts stereo to mono, resamples from 48kHz to 16kHz) and streams it to AssemblyAI's servers for real-time transcription.

## 🚀 Installation

### Prerequisites

- **Windows 10/11** (WASAPI loopback required)
- **Python 3.7+**
- **AssemblyAI API Key** ([Get one free](https://www.assemblyai.com/))

### Step 1: Clone/Download Files

Ensure you have all three core files:
- `run.py` - The main widget code
- `widget.spec` - PyInstaller configuration
- `version.txt` - Version string (e.g., `1.0.0`)

### Step 2: Install Dependencies

```bash
pip install pyaudiowpatch websocket-client numpy scipy pyinstaller

or

pip install -r requirements.txt
```

**Note**: `pyaudiowpatch` is a special fork of PyAudio that supports WASAPI loopback recording on Windows.

### Step 3: Configure API Key

Open `run.py` and paste your AssemblyAI API key:

```python
YOUR_API_KEY = "your-assemblyai-api-key-here"  # ← PASTE HERE
```

### Step 4: Run the Widget

```bash
python run.py
```

## 📦 Building Executable

The included `widget.spec` file is pre-configured for PyInstaller. To build a standalone `.exe`:

```bash
pyinstaller --clean widget.spec
```

This will create:
- `dist/Bubit.exe` - Standalone executable
- `build/` - Build artifacts (temporary)

**Before building**, update `version.txt` with your desired version number (e.g., `1.0.0`).

### What widget.spec Does

The `.spec` file configures PyInstaller to:
- Bundle all Python dependencies (`tkinter`, `numpy`, `scipy`, etc.)
- Include PyAudioWPatch and its required DLLs
- Set application metadata (name, version from `version.txt`)
- Create a single executable or folder-based distribution
- Handle Windows-specific audio libraries

## 🎮 Usage

### Widget Controls

| Element | Action | Description |
|---------|--------|-------------|
| **SUBS Toggle** | Click left pill (18px-186px) | Turn real-time subtitles ON/OFF |
| **NOTE Button** | Click right pill (196px-272px) | Enable/disable saving to `note.txt` |
| **✕ Button** | Click X circle (center 328,36) | Close application |
| **Drag** | Click-hold anywhere | Move the widget window |
| **Subtitle Bar** | Drag black window | Reposition subtitle display |

### Visual Indicators

- **Green dot** = Subtitles active, connected to AssemblyAI
- **Red dot** = Subtitles inactive
- **Blue "NOTE"** = Note-taking enabled (saves to file)
- **Gray "NOTE"** = Note-taking disabled

### Workflow

1. **Start**: Click **SUBS** toggle → turns green, subtitle window appears at bottom of screen
2. **Play Audio**: Start any audio/video (YouTube, Zoom, Spotify, etc.)
3. **Watch**: Transcripts appear live in the black subtitle bar
4. **Save**: Click **NOTE** to enable saving all transcripts with timestamps to `note.txt`
5. **Stop**: Click **SUBS** to pause, or **✕** to exit completely

### Session Timeout

The widget has a **120-second (2-minute) default session limit** to prevent accidental API overuse. After timeout:
- Streaming permanently stops
- "Session timeout - Restart app" message appears
- You must restart the application to continue

Adjust this in `run.py`:
```python
SESSION_TIMEOUT = 120  # seconds
```

## 🛠️ Technical Details

### Audio Pipeline

```python
# Configuration in run.py
INPUT_RATE = 48000      # System audio rate (WASAPI)
OUTPUT_RATE = 16000     # AssemblyAI required rate
CHANNELS = 2            # Stereo input
CHUNK = 4800            # 100ms buffers (4800 samples at 48kHz)

# Processing flow:
1. Capture: WASAPI loopback → PyAudio stream (Int16, stereo, 48kHz)
2. Process: Stereo → Mono (average channels) → Resample to 16kHz
3. Send: Binary PCM data via WebSocket to AssemblyAI
4. Receive: JSON messages with transcript text
5. Display: Update Tkinter canvas text item
```

### Key Classes & Methods

| Component | Purpose |
|-----------|---------|
| `SubtitleWidget` | Main application class |
| `__init__()` | Sets up GUI, bindings, state variables |
| `_render()` | Draws the entire UI (canvas primitives) |
| `_toggle()` | Handles ON/OFF state switching |
| `_start_streaming()` | Initializes PyAudio, finds loopback device, opens WebSocket |
| `_stream_audio()` | Thread function that reads audio and sends to WebSocket |
| `_process_audio()` | Converts stereo to mono, resamples 48kHz→16kHz |
| `_on_ws_message()` | Handles incoming transcripts from AssemblyAI |
| `_build_subtitle_window()` | Creates the floating subtitle display window |
| `set_subtitle()` | Updates the subtitle text display |

### WebSocket Events (AssemblyAI v3)

| Message Type | Description |
|--------------|-------------|
| `Begin` | Session started, contains `id` |
| `Turn` | Transcript data - contains `transcript` text and `end_of_turn` boolean |
| `Termination` | Session ended, contains `audio_duration_seconds` |

### File Output Format (note.txt)

```
==================================================
Session started: 2024-01-15 14:30:25
Language: English
==================================================

[14:30:30] Hello and welcome to the presentation
[14:30:35] Today we'll be discussing real-time transcription
[14:30:40] As you can see it's working quite well

==================================================
Session ended: 2024-01-15 14:32:25
==================================================
```

## 🎨 Customization

Edit these constants in `run.py`:

```python
# === COLORS ===
BG          = '#0d1828'    # Widget background
PANEL       = '#172135'    # Main panel
PILL_BG     = '#1a2d48'    # Toggle background
SUBS_ACTIVE = '#0d3a4e'    # Active toggle fill
DOT_GREEN   = '#14e878'    # ON indicator
DOT_RED     = '#ff2d50'    # OFF indicator
TEAL        = '#00d4b0'    # NOTE button active

# === DIMENSIONS ===
W          = 360           # Widget width
H_BASE     = 100           # Widget height
CORNER     = 18            # Corner radius

# === API CONFIG ===
CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "speech_model": "universal-streaming-english",  # or "universal-streaming-multilingual"
}
SESSION_TIMEOUT = 120      # Seconds before auto-stop
```

## 🔒 Security & API Key Management

**⚠️ Never commit your API key to version control!**

For production/distribution:

1. **Environment Variable** (Recommended):
   ```python
   import os
   YOUR_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
   ```

2. **Config File** (Add to `.gitignore`):
   ```python
   import json
   with open('config.json') as f:
       YOUR_API_KEY = json.load(f)['api_key']
   ```

3. **Temporary Tokens** (For client-side apps):
   Use AssemblyAI's temporary token endpoint to generate short-lived tokens instead of exposing your main key.

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "WASAPI not available" | Must use Windows 10/11. Run `python -m pyaudiowpatch` to check devices |
| "Loopback device not found" | Ensure speakers/headphones are connected AND audio is playing |
| No transcription | Check API key validity; ensure audio is playing; check internet connection |
| Widget not draggable | Click on the colored panel area, not the very edges |
| High latency | Check internet speed; AssemblyAI requires stable connection |
| Build fails | Ensure all dependencies installed; try `pyinstaller --clean widget.spec` |

## 📚 Dependencies

| Package | Purpose |
|---------|---------|
| `pyaudiowpatch` | WASAPI loopback audio capture |
| `websocket-client` | WebSocket connection to AssemblyAI |
| `numpy` | Audio array processing |
| `scipy` | Audio resampling (`scipy.signal.resample`) |
| `pyinstaller` | Building executable (optional) |

## 📖 References

- [AssemblyAI Streaming Documentation](https://www.assemblyai.com/docs/streaming)
- [PyAudioWPatch GitHub](https://github.com/s0d3s/PyAudioWPatch)
- [AssemblyAI Universal-Streaming API](https://assemblyai.com/docs/api-reference/streaming-api/universal-streaming/universal-streaming)

## 📝 License

MIT License - Modify and distribute freely.

---

**Made with ❤️ using AssemblyAI, PyAudioWPatch, and Tkinter**
