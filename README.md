# 🎧 Bubit - Real-Time Subtitle Widget

A sleek, floating desktop widget that provides real-time subtitles/captions for any audio playing on your Windows computer. Powered by AssemblyAI's Universal-Streaming speech recognition API.

![Bubit Widget Preview](https://img.shields.io/badge/Platform-Windows-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.7+-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## ✨ Features

- **🎙️ Real-time Transcription** - Captures system audio (speakers/headphones) and transcribes it live with ~300ms latency
- **🖥️ Floating Widget** - Minimalist, borderless window that stays on top and can be dragged anywhere
- **📝 Note Taking** - Optional feature to save all transcripts to a text file with timestamps
- **⏱️ Session Management** - 2-minute session timeout to manage API usage costs
- **🎨 Modern UI** - Dark theme with smooth animations and visual feedback
- **🔊 WASAPI Loopback** - Uses Windows Audio Session API to capture "what you hear" without virtual cables

## 🤖 How It Works

### Audio Capture Pipeline

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

### AI Technology

**AssemblyAI Universal-Streaming** 

- **Model**: `universal-streaming-english` (configurable for multilingual)
- **Latency**: ~300ms P50 (50th percentile)
- **Protocol**: WebSocket streaming at `wss://streaming.assemblyai.com/v3/ws`
- **Audio Format**: PCM 16-bit, 16kHz sample rate (resampled from 48kHz)
- **Pricing**: $0.15/hour of streaming (free tier: 333 hours/month) 

The widget captures audio from your default output device using WASAPI loopback mode , processes it in real-time (converting stereo to mono and resampling), and streams it to AssemblyAI's servers for transcription. The results appear instantly in the floating subtitle window.

## 📁 Project Structure

```
bubit/
├── main.py              # Main application code
├── requirements.txt     # Python dependencies
├── note.txt             # Generated transcript file (created at runtime)
└── README.md           # This file
```

## 🚀 Installation

### Prerequisites

- **Windows 10/11** (WASAPI loopback required)
- **Python 3.7+**
- **AssemblyAI API Key** ([Get one free](https://www.assemblyai.com/))

### Step 1: Clone or Download

```bash
git clone https://github.com/yourusername/bubit.git
cd bubit
```

### Step 2: Install Dependencies

```bash
pip install pyaudiowpatch websocket-client numpy scipy
```

**Note**: `pyaudiowpatch` is a fork of PyAudio that supports WASAPI loopback recording . It comes with pre-built wheels for Windows.

### Step 3: Configure API Key

Open `main.py` and paste your AssemblyAI API key:

```python
YOUR_API_KEY = "your-api-key-here"  # ← PASTE YOUR KEY HERE
```

Or set it as an environment variable and modify the code to read from `os.environ`.

### Step 4: Run

```bash
python main.py
```

## 🎮 Usage

### Controls

| Element | Action | Description |
|---------|--------|-------------|
| **SUBS Toggle** | Click the left pill | Turn real-time subtitles ON/OFF |
| **NOTE Button** | Click the right pill | Enable/disable saving to `note.txt` |
| **✕ Button** | Click the X | Close the application |
| **Drag** | Click and hold anywhere | Move the widget |
| **Subtitle Window** | Drag the black bar | Reposition subtitles on screen |

### Workflow

1. **Start**: Click the **SUBS** toggle to turn it ON (green indicator)
2. **Play Audio**: Start any audio/video on your computer (YouTube, Zoom, music, etc.)
3. **Watch**: Transcripts appear in the black subtitle window at the bottom of your screen
4. **Save Notes**: Click **NOTE** to save all transcripts with timestamps to `note.txt`
5. **Stop**: Click **SUBS** again to pause, or **✕** to exit

### Session Timeout

The widget has a **120-second (2-minute) session limit** to prevent accidental API overuse. After timeout:
- Streaming permanently stops
- You must restart the app to continue
- This can be adjusted by changing `SESSION_TIMEOUT` in the code

## 🛠️ Technical Details

### Audio Processing

```python
# Configuration
INPUT_RATE = 48000      # Device native rate (WASAPI)
OUTPUT_RATE = 16000     # AssemblyAI required rate
CHANNELS = 2            # Stereo input
CHUNK = 4800            # 100ms buffers

# Processing pipeline
Stereo (48kHz) → Mono (average) → Resample (16kHz) → PCM 16-bit → WebSocket
```

### WebSocket Events

| Event | Description |
|-------|-------------|
| `Begin` | Session started, contains session ID |
| `Turn` | Transcript data (partial or final) |
| `Termination` | Session ended, contains duration |

### Customization

Edit these constants in `main.py` to customize:

```python
# Colors
BG = '#0d1828'          # Widget background
PANEL = '#172135'       # Panel color
DOT_GREEN = '#14e878'   # Active indicator
DOT_RED = '#ff2d50'     # Inactive indicator

# Timeout
SESSION_TIMEOUT = 120     # Seconds (2 minutes)

# Model
CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "speech_model": "universal-streaming-english",  # or "universal-streaming-multilingual"
}
```

## 📦 Building Executable (Optional)

To create a standalone `.exe` using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-binary "path\to\portaudio.dll;." main.py
```

**Note**: You may need to include additional DLLs for PyAudioWPatch to work in the bundled executable.

## 🔒 Security Notes

- **API Key**: Never commit your API key to version control. Use environment variables for production.
- **Temporary Tokens**: For client-side apps, use AssemblyAI's temporary token feature instead of hardcoding keys 
- **Audio Data**: Audio is streamed to AssemblyAI's servers for processing. Review their [privacy policy](https://www.assemblyai.com/legal/privacy-policy).

## 🐛 Troubleshooting

### "WASAPI not available"
- Ensure you're on Windows 10/11
- Run `python -m pyaudiowpatch` to list available devices 

### "Default loopback output device not found"
- Make sure speakers/headphones are connected
- Audio must be PLAYING for loopback to detect the device
- Check Windows Sound Settings → Recording devices

### No transcription appearing
- Verify your API key is valid
- Check that audio is actually playing (system volume up)
- Look at console output for WebSocket errors

### High latency
- Ensure stable internet connection
- Check AssemblyAI [status page](https://status.assemblyai.com/) for API issues

## 📚 API Reference

- [AssemblyAI Streaming Docs](https://www.assemblyai.com/docs/streaming)
- [Universal-Streaming API](https://assemblyai.com/docs/api-reference/streaming-api/universal-streaming/universal-streaming) 
- [PyAudioWPatch GitHub](https://github.com/s0d3s/PyAudioWPatch) 

## 📝 License

MIT License - Feel free to modify and distribute.

---

**Made with ❤️ using AssemblyAI & PyAudioWPatch**
