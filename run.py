import tkinter as tk
import platform
import sys
import os

# Audio & WebSocket imports
import pyaudiowpatch as pyaudio
import websocket
import json
import threading
import time
import numpy as np
from scipy.signal import resample
from urllib.parse import urlencode

from datetime import datetime
#════════════════════════════════════════════════════════════════════

NOTES_FILE = "note.txt"     # File to store all subtitles

NOTES_TOGGLE_X1 = 196     # Note toggle X start
NOTES_TOGGLE_X2 = 272     # Note toggle X end
NOTES_TOGGLE_Y1 = 18      # Note toggle Y start  
NOTES_TOGGLE_Y2 = 54      # Note toggle Y end

YOUR_API_KEY = ""  # <-- PASTE YOUR ASSEMBLYAI API KEY HERE

INPUT_RATE = 48000      # Speaker output rate (usually 48000)
OUTPUT_RATE = 16000     # AssemblyAI required sample rate
CHANNELS = 2            # Stereo (speakers are usually stereo)
CHUNK = 4800            # Audio buffer size (100ms at 48kHz)
DEVICE_INDEX = None     # Auto-detect WASAPI loopback device

# AssemblyAI Endpoint
CONNECTION_PARAMS = {
"sample_rate": 16000,
"speech_model": "universal-streaming-english",
}
API_ENDPOINT = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(CONNECTION_PARAMS)}"

SESSION_TIMEOUT = 120

BG          = '#0d1828'
PANEL       = '#172135'
PANEL_GRAD  = '#1e2d4a'
BORDER      = '#2d4468'
BORDER_LT   = '#3a5580'

PILL_BG     = '#1a2d48'
SUBS_ACTIVE = '#0d3a4e'
SUBS_BORDER = '#1e5068'
OFF_FG      = '#4e6280'

DOT_GREEN   = '#14e878'
DOT_RED     = '#ff2d50'
GLOW_GREEN  = '#0a5c3a'
GLOW_RED    = '#5c1020'

CLOSE_BG    = '#1e2e4a'
CLOSE_FG    = '#6878a0'
CLOSE_HV    = '#ff4060'

WHITE       = '#ffffff'
TEAL        = '#00d4b0'

SUB_BG      = '#000000'
SUB_FG      = '#ffffff'


def round_rect(cv, x1, y1, x2, y2, r=12, **kw):
    """Draw a smooth rounded rectangle on a Canvas."""
    pts = [
        x1 + r, y1,       x2 - r, y1,
        x2,     y1,       x2,     y1 + r,
        x2,     y2 - r,   x2,     y2,
        x2 - r, y2,       x1 + r, y2,
        x1,     y2,       x1,     y2 - r,
        x1,     y1 + r,   x1,     y1,
    ]
    return cv.create_polygon(pts, smooth=True, **kw)

class SubtitleWidget:
    """Main application class combining GUI and AssemblyAI streaming."""

    # Widget dimensions
    W          = 360
    H_BASE     = 100
    CORNER     = 18

    # Toggle pill coordinates
    TOGGLE_X1  = 18
    TOGGLE_X2  = 186
    TOGGLE_Y1  = 18
    TOGGLE_Y2  = 54

    # Close button coordinates
    CLOSE_CX   = 328
    CLOSE_CY   = 36
    CLOSE_R    = 16

    def __init__(self):
        """Initialize the widget and all components."""
        # ─── GUI Setup ─────────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title('Bubit')
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.config(bg=BG)

        # Windows transparency
        if platform.system() == 'Windows':
            self.root.attributes('-alpha', 0.97)

        # State variables
        self.is_on = False
        self.notes_enabled = False  # Note taking toggle state
        self.close_hovered = False

        # Session timeout tracking
        self.session_permanently_stopped = False  # Permanent stop flag
        self.session_start_time = None
        self.timeout_check_id = None

        # Center window on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'+{sw // 2 - self.W // 2}+{sh // 2 - 160}')

        # Create main canvas
        self.cv = tk.Canvas(
            self.root, width=self.W, height=self.H_BASE,
            bg=BG, highlightthickness=0
        )
        self.cv.pack(fill='both', expand=True)

        # Drag state variables
        self._dx = 0
        self._dy = 0
        self._is_dragging = False

        # Bind mouse events
        self.cv.bind('<ButtonPress-1>',   self._on_press)
        self.cv.bind('<B1-Motion>',       self._on_drag)
        self.cv.bind('<ButtonRelease-1>', self._on_release)
        self.cv.bind('<Motion>',          self._on_hover)
        self.cv.bind('<Leave>',           self._on_leave)

        # ─── Audio/WebSocket State ───────────────────────────────────────────────
        self.audio = None           # PyAudio instance
        self.stream = None          # Audio stream
        self.ws = None              # WebSocket connection
        self.ws_thread = None       # WebSocket thread
        self.audio_thread = None    # Audio streaming thread
        self.stop_event = threading.Event()  # Thread control event
        self.current_subtitle = ""  # Current subtitle text

        self.notes_file = None      # File handle for notes

        # ─── Build Subtitle Window ───────────────────────────────────────────────
        self._build_subtitle_window()

        # Initial render
        self._render()

        # Start main loop
        self.root.mainloop()

    def _render(self):
        """Render the entire widget UI."""
        cv = self.cv
        cv.delete('all')

        W = self.W
        H = self.H_BASE

        # Update canvas size
        cv.config(height=H)
        self.root.geometry(f'{W}x{H}')

        # ── Outer Panel ─────────────────────────────────────────────────────────
        round_rect(cv, 1, 1, W - 1, H - 1, self.CORNER,
                   fill=PANEL, outline=BORDER, width=1)
        # Subtle inner highlight (top edge gradient effect)
        round_rect(cv, 2, 2, W - 2, H // 3, self.CORNER,
                   fill=PANEL_GRAD, outline='')

        # ── Toggle Pill ───────────────────────────────────────────────────────────
        tx1, ty1 = self.TOGGLE_X1, self.TOGGLE_Y1
        tx2, ty2 = self.TOGGLE_X2, self.TOGGLE_Y2
        mid_x = (tx1 + tx2) // 2

        # Pill background
        round_rect(cv, tx1, ty1, tx2, ty2, 16,
                   fill=PILL_BG, outline=BORDER, width=1)

        # SUBS side active fill (when ON)
        if self.is_on:
            round_rect(cv, tx1 + 1, ty1 + 1, mid_x, ty2 - 1, 15,
                       fill=SUBS_ACTIVE, outline=SUBS_BORDER, width=1)

        # Indicator dot with glow
        dot_cx = tx1 + 18
        dot_cy = (ty1 + ty2) // 2
        dot_r = 6

        # Choose colors based on state
        glow_c = GLOW_GREEN if self.is_on else GLOW_RED
        dot_c = DOT_GREEN if self.is_on else DOT_RED

        # Glow rings
        for gr, ga in [(11, glow_c), (8, glow_c)]:
            cv.create_oval(dot_cx - gr, dot_cy - gr,
                           dot_cx + gr, dot_cy + gr,
                           fill=ga, outline='')

        # Main dot
        cv.create_oval(dot_cx - dot_r, dot_cy - dot_r,
                       dot_cx + dot_r, dot_cy + dot_r,
                       fill=dot_c, outline='')

        # Bright center
        cv.create_oval(dot_cx - 2, dot_cy - 2,
                       dot_cx + 2, dot_cy + 2,
                       fill='#ffffff', outline='')

        # SUBS label
        subs_x = dot_cx + 26
        cv.create_text(subs_x, dot_cy, text='SUBS',
                       fill=WHITE, font=('Helvetica', 11, 'bold'), anchor='center')

        # ON/OFF label - shows ON when active, OFF when inactive
        off_x = mid_x + 24
        status_text = 'ON' if self.is_on else 'OFF'
        status_color = WHITE if self.is_on else OFF_FG
        cv.create_text(off_x, dot_cy, text=status_text,
                       fill=status_color, font=('Helvetica', 11, 'bold' if self.is_on else ''), anchor='center')

        # ── Notes Toggle Pill ────────────────────────────────────────────────────
        nx1, ny1 = NOTES_TOGGLE_X1, NOTES_TOGGLE_Y1
        nx2, ny2 = NOTES_TOGGLE_X2, NOTES_TOGGLE_Y2
        ncy = (ny1 + ny2) // 2

        # Pill background
        round_rect(cv, nx1, ny1, nx2, ny2, 12,
                   fill=PILL_BG, outline=BORDER, width=1)

        # Active fill when notes enabled
        if self.notes_enabled:
            round_rect(cv, nx1 + 1, ny1 + 1, nx2 - 1, ny2 - 1, 11,
                       fill=SUBS_ACTIVE, outline=SUBS_BORDER, width=1)

        # Note icon/text
        note_x = (nx1 + nx2) // 2
        note_color = TEAL if self.notes_enabled else OFF_FG
        cv.create_text(note_x, ncy, text='NOTE',
                       fill=note_color, font=('Helvetica', 9, 'bold'))

        # ── Close Button ─────────────────────────────────────────────────────────
        ccx, ccy, cr = self.CLOSE_CX, self.CLOSE_CY, self.CLOSE_R
        close_border = CLOSE_HV if self.close_hovered else BORDER
        close_fg = CLOSE_HV if self.close_hovered else CLOSE_FG

        cv.create_oval(ccx - cr, ccy - cr, ccx + cr, ccy + cr,
                       fill=CLOSE_BG, outline=close_border, width=1)
        cv.create_text(ccx, ccy, text='✕', fill=close_fg,
                       font=('Helvetica', 10, 'bold'))

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLING
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_press(self, e):
        """Handle mouse button press for dragging."""
        self._dx = e.x
        self._dy = e.y
        self._is_dragging = False

    def _on_drag(self, e):
        """Handle mouse drag to move window."""
        dx = e.x - self._dx
        dy = e.y - self._dy

        if abs(dx) > 3 or abs(dy) > 3:
            self._is_dragging = True

        if self._is_dragging:
            nx = self.root.winfo_x() + dx
            ny = self.root.winfo_y() + dy
            self.root.geometry(f'+{nx}+{ny}')

    def _on_release(self, e):
        """Handle mouse button release - check for clicks."""
        if self._is_dragging:
            return

        x, y = e.x, e.y

        # Check Close button click
        if self._in_circle(x, y, self.CLOSE_CX, self.CLOSE_CY, self.CLOSE_R):
            self._cleanup_and_exit()
            return

        # Check Toggle pill click
        if (self.TOGGLE_X1 <= x <= self.TOGGLE_X2 and
                self.TOGGLE_Y1 <= y <= self.TOGGLE_Y2):
            self._toggle()
            return

        # Check Notes toggle click
        if (NOTES_TOGGLE_X1 <= x <= NOTES_TOGGLE_X2 and
                NOTES_TOGGLE_Y1 <= y <= NOTES_TOGGLE_Y2):
            self.notes_enabled = not self.notes_enabled
            # Open/close notes file based on state
            if self.notes_enabled and self.is_on and not self.notes_file:
                self._open_notes_file()
            elif not self.notes_enabled and self.notes_file:
                self._close_notes_file()
            self._render()
            return

    def _on_hover(self, e):
        """Handle mouse hover for visual feedback."""
        x, y = e.x, e.y

        # Check close button hover
        close_now = self._in_circle(x, y, self.CLOSE_CX, self.CLOSE_CY, self.CLOSE_R)

        # Check notes toggle hover
        notes_hover = (NOTES_TOGGLE_X1 <= x <= NOTES_TOGGLE_X2 and
                       NOTES_TOGGLE_Y1 <= y <= NOTES_TOGGLE_Y2)

        # Update if changed
        if close_now != self.close_hovered:
            self.close_hovered = close_now
            self._render()
            # Change cursor
            self.cv.config(cursor='hand2' if (close_now or notes_hover) else '')

    def _on_leave(self, e):
        """Handle mouse leaving the widget."""
        if self.close_hovered:
            self.close_hovered = False
            self._render()

    def _toggle(self):
        """Toggle subtitles ON/OFF."""
        # Check if permanently stopped
        if self.session_permanently_stopped:
            print("⚠ Session permanently stopped due to timeout. Restart app to continue.")
            return

        self.is_on = not self.is_on
        self._render()

        if self.is_on:
            # Show subtitle window and start streaming
            self.sub_win.deiconify()
            self.sub_win.lift()
            # Open notes file only if notes enabled
            if self.notes_enabled:
                self._open_notes_file()
            self._start_streaming()
        else:
            # Hide subtitle window and stop streaming
            self.sub_win.withdraw()
            self._close_notes_file()
            self._stop_streaming()

    def _open_notes_file(self):
        """Open notes file for writing subtitles."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.notes_file = open(NOTES_FILE, 'a', encoding='utf-8')
            self.notes_file.write(f"\n{'='*50}\n")
            self.notes_file.write(f"Session started: {timestamp}\n")
            self.notes_file.write(f"Language: English\n")
            self.notes_file.write(f"{'='*50}\n\n")
            self.notes_file.flush()
            print(f"📝 Notes file opened: {NOTES_FILE}")
        except Exception as e:
            print(f"⚠️ Failed to open notes file: {e}")
            self.notes_file = None

    def _close_notes_file(self):
        """Close notes file."""
        if self.notes_file:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.notes_file.write(f"\n{'='*50}\n")
                self.notes_file.write(f"Session ended: {timestamp}\n")
                self.notes_file.write(f"{'='*50}\n")
                self.notes_file.close()
                print(f"📝 Notes file closed")
            except Exception as e:
                print(f"⚠️ Error closing notes file: {e}")
            finally:
                self.notes_file = None

    @staticmethod
    def _in_circle(x, y, cx, cy, r):
        """Check if point (x,y) is inside circle centered at (cx,cy) with radius r."""
        return (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2

    # ═══════════════════════════════════════════════════════════════════════════
    # SUBTITLE WINDOW
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_subtitle_window(self):
        """Create the subtitle display window."""
        SW, SH = 640, 120  # Window size

        self.sub_win = tk.Toplevel(self.root)
        self.sub_win.title('Subtitles')
        self.sub_win.overrideredirect(True)
        self.sub_win.config(bg='black')
        self.sub_win.withdraw()  # Hidden initially

        # Position at bottom-center of screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        sx = sw // 2 - SW // 2
        sy = sh - SH - 60
        self.sub_win.geometry(f'{SW}x{SH}+{sx}+{sy}')

        # Canvas for rounded black box
        self.sub_cv = tk.Canvas(
            self.sub_win, width=SW, height=SH,
            bg='black', highlightthickness=0
        )
        self.sub_cv.pack(fill='both', expand=True)

        round_rect(self.sub_cv, 4, 4, SW - 4, SH - 4, 16,
                   fill='#0a0a0a', outline='#1e1e1e', width=1)

        # Subtitle text
        self.sub_text_id = self.sub_cv.create_text(
            SW // 2, SH // 2,
            text='Waiting for speech...',
            fill=SUB_FG,
            font=('Helvetica', 16),
            width=SW - 40,
            justify='center',
            anchor='center'
        )

        # Drag bindings for subtitle window
        self._sdx = 0
        self._sdy = 0
        self.sub_cv.bind('<ButtonPress-1>', self._sub_press)
        self.sub_cv.bind('<B1-Motion>', self._sub_drag)

    def _sub_press(self, e):
        """Start dragging subtitle window."""
        self._sdx = e.x
        self._sdy = e.y

    def _sub_drag(self, e):
        """Drag subtitle window."""
        dx = e.x - self._sdx
        dy = e.y - self._sdy
        nx = self.sub_win.winfo_x() + dx
        ny = self.sub_win.winfo_y() + dy
        self.sub_win.geometry(f'+{nx}+{ny}')

    def set_subtitle(self, text: str):
        """Update the subtitle text display."""
        self.current_subtitle = text
        if hasattr(self, 'sub_cv') and self.sub_cv.winfo_exists():
            self.sub_cv.itemconfig(self.sub_text_id, text=text)

    def _start_streaming(self):
        """Start the AssemblyAI streaming session using WASAPI loopback."""
        if not YOUR_API_KEY:
            self.set_subtitle("Error: Please set YOUR_API_KEY")
            print("❌ Error: Please set YOUR_API_KEY in the configuration section")
            return

        # Reset stop event
        self.stop_event.clear()

        # Record session start time
        self.session_start_time = time.time()

        # Start timeout checker
        self._check_timeout()

        # Initialize PyAudio with WASAPI loopback
        try:
            self.audio = pyaudio.PyAudio()
            
            # Get default WASAPI info
            try:
                wasapi_info = self.audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            except OSError:
                raise Exception("WASAPI not available on this system")
            
            # Get default WASAPI speakers (output device)
            default_speakers = self.audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            print(f"🎧 Default speakers: {default_speakers['name']}")
            
            # Check if it's already a loopback device
            if not default_speakers.get("isLoopbackDevice", False):
                # Find the loopback device with same name + [Loopback] suffix
                loopback_found = False
                for loopback in self.audio.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        loopback_found = True
                        print(f"✅ Found loopback: {loopback['name']}")
                        break
                
                if not loopback_found:
                    raise Exception("Default loopback output device not found. Run `python -m pyaudiowpatch` to check available devices.")
            else:
                print(f"✅ Speakers are already loopback device")
            
            # Use device's actual sample rate and channels
            device_rate = int(default_speakers["defaultSampleRate"])
            device_channels = default_speakers["maxInputChannels"]
            
            print(f"   Sample Rate: {device_rate}Hz, Channels: {device_channels}")
            print(f"   Device Index: {default_speakers['index']}")
            
            # Open stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_rate,
                input=True,
                input_device_index=default_speakers["index"],
                frames_per_buffer=CHUNK,
            )
            
            print(f"✅ Audio stream opened - Capturing system audio while you hear it")
            self.set_subtitle("Listening...")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Audio Error: {error_msg}")
            self.set_subtitle(f"Audio Error: Check setup")
            print("⚠️  TROUBLESHOOTING:")
            print("   1. Make sure speakers or headphones are CONNECTED")
            print("   2. Make sure audio is PLAYING (YouTube, music, etc.)")
            print("   3. Run: python -m pyaudiowpatch")
            print("   4. Check that a loopback device exists")
            
            # Cleanup
            if self.audio:
                try:
                    self.audio.terminate()
                except:
                    pass
                self.audio = None
            return

        # Start WebSocket connection in a thread
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

    def _check_timeout(self):
        """Check if session has exceeded timeout limit."""
        if not self.is_on or self.session_permanently_stopped:
            return

        elapsed = time.time() - self.session_start_time

        if elapsed >= SESSION_TIMEOUT:
            # Timeout reached - permanently stop
            print(f"\n⏰ Session timeout ({SESSION_TIMEOUT}s reached) - Permanently stopping")
            self.set_subtitle(f"Session timeout ({SESSION_TIMEOUT}s) - Restart app")
            self.session_permanently_stopped = True
            self._stop_streaming()
            self.is_on = False
            self._render()
            self.sub_win.withdraw()
            return

        # Schedule next check (every 1 second)
        self.timeout_check_id = self.root.after(1000, self._check_timeout)

    def _run_websocket(self):
        """Run WebSocket connection (called in thread)."""
        self.ws = websocket.WebSocketApp(
            API_ENDPOINT,
            header={"Authorization": YOUR_API_KEY},
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )
        self.ws.run_forever()

    def _on_ws_open(self, ws):
        """Handle WebSocket connection open."""
        print("🎧 Connected to AssemblyAI - Listening...")
        self.set_subtitle("Listening...")

        # Start audio streaming thread
        self.audio_thread = threading.Thread(target=self._stream_audio, args=(ws,), daemon=True)
        self.audio_thread.start()

    def _stream_audio(self, ws):
        """Stream audio data to WebSocket."""
        seconds_per_chunk = CHUNK / INPUT_RATE

        while not self.stop_event.is_set():
            try:
                # Read audio data
                data = self.stream.read(CHUNK, exception_on_overflow=False)

                # Process audio (stereo to mono, resample)
                processed = self._process_audio(data)

                # Send to WebSocket
                ws.send(processed, websocket.ABNF.OPCODE_BINARY)

                # Maintain timing
                time.sleep(seconds_per_chunk)

            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"\n⚠ Audio streaming error: {e}")
                break

    def _process_audio(self, data):
        """Process audio: convert bytes -> numpy, stereo to mono, resample."""
        # Convert bytes to numpy array
        audio_data = np.frombuffer(data, dtype=np.int16)

        # Stereo to mono (average channels)
        mono = audio_data.reshape(-1, 2).mean(axis=1)

        # Resample 48kHz -> 16kHz
        num_samples = int(len(mono) * OUTPUT_RATE / INPUT_RATE)
        resampled = resample(mono, num_samples)

        return resampled.astype(np.int16).tobytes()

    def _on_ws_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "Turn":
                text = data.get("transcript", "")
                end_of_turn = data.get("end_of_turn", False)

                if end_of_turn:
                    # Final transcript for this turn
                    print(f"\n📝 Transcript: {text}")
                    self.set_subtitle(text)
                    self._save_to_notes(text)
                else:
                    # Partial transcript (interim results)
                    self.set_subtitle(text)

            elif msg_type == "Begin":
                session_id = data.get("id", "unknown")
                print(f"✅ Session started: {session_id}")

            elif msg_type == "Termination":
                duration = data.get("audio_duration_seconds", 0)
                print(f"🔌 Session terminated. Duration: {duration:.1f}s")

        except json.JSONDecodeError:
            print("⚠ Failed to parse message")

    def _save_to_notes(self, text: str):
        """Save subtitle to notes file."""
        if not self.notes_file:
            return
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.notes_file.write(f"[{timestamp}] {text}\n\n")
            self.notes_file.flush()
        except Exception as e:
            print(f"⚠️ Failed to write to notes: {e}")

    def _on_ws_error(self, ws, error):
        """Handle WebSocket errors."""
        print(f"\n❌ WebSocket Error: {error}")
        self.set_subtitle(f"Connection Error")
        self.stop_event.set()

    def _on_ws_close(self, ws, code, msg):
        """Handle WebSocket connection close."""
        if not self.stop_event.is_set():
            print("\n🔌 Disconnected from AssemblyAI")
        self.stop_event.set()

    def _stop_streaming(self):
        """Stop the streaming session and cleanup resources."""
        # Signal threads to stop
        self.stop_event.set()

        # Cancel timeout checker
        if self.timeout_check_id:
            self.root.after_cancel(self.timeout_check_id)
            self.timeout_check_id = None

        # Close WebSocket
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

        # Stop audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None

        # Terminate PyAudio
        if self.audio:
            try:
                self.audio.terminate()
            except:
                   pass
            self.audio = None

        print("⏹ Streaming stopped")
        self.set_subtitle("Press SUBS to start")

    def _cleanup_and_exit(self):
        """Cleanup resources and exit application."""
        self._stop_streaming()
        self._close_notes_file()
        self.root.destroy()

if __name__ == '__main__':
    app = SubtitleWidget()