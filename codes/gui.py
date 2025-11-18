import customtkinter as ctk
import threading
import asyncio
import queue
import tkinter as tk
from collections import deque

import codes.llm_handler
import codes.stt_handler
import codes.tts_handler


class Indicator:
    """A visual indicator for processing steps (STT, LLM, TTS)."""

    def __init__(self, parent, text):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.label = ctk.CTkLabel(
            self.frame,
            text=text,
            font=("Segoe UI", 10, "bold"),
            text_color=("#888888", "#707070"),
        )
        self.label.pack(side="left")
        self.dot = ctk.CTkLabel(
            self.frame,
            text="●",
            font=("Arial", 14),
            text_color=("#CCCCCC", "#4A4A4A"),
        )
        self.dot.pack(side="left", padx=3)

    def set_state(self, state: str):
        """Sets the indicator state ('inactive', 'active', 'success')."""
        colors = {
            "inactive": ("#CCCCCC", "#4A4A4A"),
            "active": ("#0078D4", "#4A9FFF"),
            "success": ("#4CAF50", "#66BB6A"),
        }
        self.dot.configure(text_color=colors.get(state, ("#CCCCCC", "#4A4A4A")))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


class WaveBubble(ctk.CTkFrame):
    """Small waveform visual that mirrors live microphone amplitude."""

    def __init__(self, parent, width=110, height=46, sample_count=28):
        self.canvas = None
        super().__init__(parent, fg_color="transparent")
        self.width = width
        self.height = height
        self.sample_count = sample_count
        self.samples = deque([0.0] * sample_count, maxlen=sample_count)
        self.active = False
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg="#141414",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.gradient = self._build_gradient()

    def _build_gradient(self):
        try:
            from wavesurfer import utils as ws_utils  # type: ignore

            cmap = ws_utils.get_cmap("magma")
            gradient = [self._rgba_to_hex(color[:3]) for color in cmap[::16][:6]]
        except Exception:
            gradient = ["#00E3AE", "#00B4D8", "#0096C7", "#7209B7", "#F72585"]
        return gradient

    @staticmethod
    def _rgba_to_hex(rgb_slice):
        r, g, b = (int(max(0, min(1, c)) * 255) for c in rgb_slice)
        return f"#{r:02x}{g:02x}{b:02x}"

    def set_active(self, is_active: bool):
        self.active = is_active
        bg = ("#F0F0F0", "#1F1F1F") if is_active else ("#FAFAFA", "#141414")
        try:
            # Handle both light and dark modes
            current_mode = ctk.get_appearance_mode()
            bg_color = bg[0] if current_mode == "Light" else bg[1]
            self.canvas.configure(bg=bg_color)
        except:
            self.canvas.configure(bg="#1F1F1F" if is_active else "#141414")
        self._draw()

    def push_sample(self, amplitude: float):
        self.samples.append(max(0.0, min(1.0, amplitude)))
        self._draw()

    def decay(self, rate: float = 0.07):
        if not self.samples:
            return
        last = max(0.0, self.samples[-1] - rate)
        self.push_sample(last)

    def reset(self):
        self.samples = deque([0.0] * self.sample_count, maxlen=self.sample_count)
        self._draw()

    def _draw(self, *_args, **_kwargs):
        if not self.canvas:
            return
        self.canvas.delete("wave")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        mid_y = height / 2
        bar_width = width / max(1, len(self.samples))

        for idx, sample in enumerate(self.samples):
            amplitude = sample * (height / 2 - 4)
            x = idx * bar_width + bar_width / 2
            color = (
                self.gradient[idx % len(self.gradient)] if self.active else "#555555"
            )
            self.canvas.create_line(
                x,
                mid_y - amplitude,
                x,
                mid_y + amplitude,
                fill=color,
                width=max(2, bar_width * 0.65),
                capstyle=tk.ROUND,
                tags="wave",
            )


class VoiceChatGUI(ctk.CTk):
    """The main GUI class for the AI Chatbot application."""

    def __init__(self, loop):
        super().__init__()
        self.async_loop = loop
        self.audio_queue = queue.Queue()
        self.tts_enabled = True  # TTS is on by default
        self.listening = False
        self.stt_worker_active = False
        self.mic_stop_event = threading.Event()
        self.mic_thread = None

        self.title("Sophia AI Assistant")
        try:
            self.iconbitmap("aura.ico")
        except:
            pass

        self.geometry("880x780")
        self.minsize(650, 550)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Modern window styling
        self.configure(fg_color=("#E8EAED", "#121212"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Create UI Panels ---
        self._create_header()
        self._create_chat_panel()
        self._create_status_bar()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(500, self.show_initial_greeting)
        self.after(250, self._update_waveform)

    def _configure_chat_tags(self):
        """Configure chat display tags based on current theme."""
        current_mode = ctk.get_appearance_mode().lower()
        is_dark = current_mode == "dark"
        
        # User message bubble
        self.chat_display.tag_config(
            "user_bubble",
            justify="right",
            rmargin=20,
            lmargin1=100,
            foreground="#FFFFFF",
            background="#0078D4",
            spacing1=6,
            spacing3=6,
            relief="flat",
            borderwidth=0,
        )
        
        # AI message bubble
        self.chat_display.tag_config(
            "ai_bubble",
            justify="left",
            lmargin1=20,
            lmargin2=20,
            rmargin=100,
            foreground="#1F1F1F" if not is_dark else "#E8E8E8",
            background="#F0F2F5" if not is_dark else "#2D2D2D",
            spacing1=6,
            spacing3=6,
            relief="flat",
            borderwidth=0,
        )
        
        # Header tags (name + timestamp)
        self.chat_display.tag_config(
            "user_header",
            justify="right",
            rmargin=20,
            foreground="#0078D4" if not is_dark else "#4A9FFF",
            spacing1=12,
            spacing3=2,
        )
        
        self.chat_display.tag_config(
            "ai_header",
            justify="left",
            lmargin1=20,
            foreground="#6C3BA6" if not is_dark else "#B084E0",
            spacing1=12,
            spacing3=2,
        )
        
        # Timestamp styling
        self.chat_display.tag_config(
            "timestamp",
            foreground="#888888" if not is_dark else "#707070",
        )

    def _create_header(self):
        """Creates a modern header with gradient accent."""
        header = ctk.CTkFrame(
            self,
            height=65,
            corner_radius=0,
            fg_color=("#F8F9FA", "#1E1E1E"),
        )
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)
        
        # Add bottom border accent
        accent_line = ctk.CTkFrame(
            header,
            height=2,
            fg_color=("#0078D4", "#0078D4"),
        )
        accent_line.pack(side="bottom", fill="x")
        
        # Title with icon
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)
        
        title = ctk.CTkLabel(
            title_frame,
            text="✨ Sophia",
            font=("Segoe UI", 24, "bold"),
            text_color=("#1A1A1A", "#FFFFFF"),
        )
        title.pack(side="left")
        
        subtitle = ctk.CTkLabel(
            title_frame,
            text="AI Assistant",
            font=("Segoe UI", 11),
            text_color=("#666666", "#888888"),
        )
        subtitle.pack(side="left", padx=(8, 0), pady=(6, 0))
        
        # Right side buttons
        button_frame = ctk.CTkFrame(header, fg_color="transparent")
        button_frame.pack(side="right", padx=15)
        
        self.header_theme_button = ctk.CTkButton(
            button_frame,
            text="🌙",
            width=35,
            height=35,
            font=("Arial", 16),
            corner_radius=17,
            command=self.toggle_theme,
            fg_color=("#E8E8E8", "#2B2B2B"),
            hover_color=("#D0D0D0", "#3B3B3B"),
            border_width=0,
        )
        self.header_theme_button.pack(side="right", padx=5)
        
        self.header_tts_button = ctk.CTkButton(
            button_frame,
            text="🔊",
            width=35,
            height=35,
            font=("Arial", 16),
            corner_radius=17,
            command=self.toggle_tts,
            fg_color=("#E8E8E8", "#2B2B2B"),
            hover_color=("#D0D0D0", "#3B3B3B"),
            border_width=0,
        )
        self.header_tts_button.pack(side="right", padx=5)

    def _create_chat_panel(self):
        """Creates the main chat panel that fills the window."""
        container_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=("#E8EAED", "#121212"),
        )
        container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        container_frame.grid_rowconfigure(0, weight=1)
        container_frame.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(
            container_frame,
            font=("Segoe UI", 13),
            corner_radius=0,
            border_width=0,
            fg_color=("#FFFFFF", "#1A1A1A"),
            wrap="word",
            state="disabled",
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Professional message bubble styling
        self._configure_chat_tags()

        input_container = ctk.CTkFrame(
            container_frame,
            fg_color=("#F8F9FA", "#1E1E1E"),
            corner_radius=0,
            border_width=0,
        )
        input_container.grid(row=1, column=0, padx=0, pady=0, sticky="ew")
        
        # Add top border
        top_border = ctk.CTkFrame(
            input_container,
            height=1,
            fg_color=("#D0D0D0", "#2A2A2A"),
        )
        top_border.pack(side="top", fill="x")
        
        input_frame = ctk.CTkFrame(input_container, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=14)
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_columnconfigure(1, weight=0)
        input_frame.grid_columnconfigure(2, weight=0)

        self.chat_entry = ctk.CTkEntry(
            input_frame,
            font=("Segoe UI", 14),
            placeholder_text="💬 Type your message...",
            height=50,
            corner_radius=25,
            border_width=2,
            border_color=("#D0D0D0", "#3A3A3A"),
            fg_color=("#FFFFFF", "#252525"),
        )
        self.chat_entry.grid(row=0, column=0, sticky="ew", ipady=2)
        self.chat_entry.bind("<Return>", self.handle_text_input)
        self.chat_entry.bind(
            "<FocusIn>",
            lambda e: self.chat_entry.configure(border_color=("#0078D4", "#0078D4"))
        )
        self.chat_entry.bind(
            "<FocusOut>",
            lambda e: self.chat_entry.configure(border_color=("#D0D0D0", "#3A3A3A"))
        )

        self.wave_bubble = WaveBubble(input_frame)
        self.wave_bubble.grid(row=0, column=1, padx=10)
        self.wave_bubble.grid_remove()

        self.mic_button = ctk.CTkButton(
            input_frame,
            text="🎙️",
            width=48,
            height=48,
            font=("Arial", 20),
            corner_radius=24,
            command=self.handle_mic_input,
            fg_color=("#0078D4", "#0066B8"),
            hover_color=("#005A9E", "#0078D4"),
            border_width=0,
        )
        self.mic_button.grid(row=0, column=2, padx=(10, 0))

    def _create_status_bar(self):
        """Creates the bottom status bar with an improved layout."""
        status_bar = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=("#FAFAFA", "#141414"),
            border_width=0,
            height=50,
        )
        status_bar.grid(row=2, column=0, sticky="ew", pady=(0, 0))
        status_bar.grid_rowconfigure(0, pad=5)
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_columnconfigure(1, weight=0)
        status_bar.grid_columnconfigure(2, weight=1)

        # --- Left side: Status Label ---
        self.status_label = ctk.CTkLabel(
            status_bar,
            text="✨ Ready",
            font=("Segoe UI", 10),
            text_color=("#666666", "#999999"),
        )
        self.status_label.grid(row=0, column=0, padx=20, sticky="w")

        # --- Center: Process Indicators ---
        indicator_frame = ctk.CTkFrame(status_bar, fg_color="transparent")
        indicator_frame.grid(
            row=0, column=1, sticky="ns"
        )  # Center the frame in the column

        self.stt_indicator = Indicator(indicator_frame, "STT")
        self.stt_indicator.pack(side="left", padx=8)
        self.llm_indicator = Indicator(indicator_frame, "LLM")
        self.llm_indicator.pack(side="left", padx=8)
        self.tts_indicator = Indicator(indicator_frame, "TTS")
        self.tts_indicator.pack(side="left", padx=8)

        # --- Right side: Provider info ---
        right_group = ctk.CTkFrame(status_bar, fg_color="transparent")
        right_group.grid(row=0, column=2, padx=20, sticky="e")

        self.provider_label = ctk.CTkLabel(
            right_group,
            text="🤖 Provider: N/A",
            font=("Segoe UI", 10),
            text_color=("#666666", "#999999"),
        )
        self.provider_label.pack(side="right")

    def toggle_theme(self):
        """Toggles the UI theme between light and dark mode."""
        current_mode = ctk.get_appearance_mode()
        new_mode = "light" if current_mode.lower() == "dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        # Show sun icon in light mode, moon icon in dark mode
        button_text = "☀️" if new_mode == "light" else "🌙"
        self.header_theme_button.configure(text=button_text)
        # Reconfigure chat tags for new theme
        self._configure_chat_tags()

    def toggle_tts(self):
        """Toggles the text-to-speech functionality on or off."""
        self.tts_enabled = not self.tts_enabled
        button_text = "🔊" if self.tts_enabled else "🔇"
        self.header_tts_button.configure(text=button_text)

    def _safe_ui(self, callback, *args, **kwargs):
        """Ensures UI mutations run on the Tk main thread."""
        if threading.current_thread() is threading.main_thread():
            callback(*args, **kwargs)
        else:
            self.after(0, lambda: callback(*args, **kwargs))

    def show_initial_greeting(self):
        self.update_chat_display(
            "Sophia", "I'm Sophia, your AI assistant. How can I help you today?"
        )

    def update_chat_display(self, sender, message):
        from datetime import datetime
        self.chat_display.configure(state="normal")
        
        timestamp = datetime.now().strftime("%H:%M")
        is_user = sender == "You"
        
        # Insert header (name + timestamp)
        header_tag = "user_header" if is_user else "ai_header"
        header_text = f"{sender} • {timestamp}\n"
        self.chat_display.insert(ctk.END, header_text, (header_tag, "timestamp"))
        
        # Insert message bubble
        bubble_tag = "user_bubble" if is_user else "ai_bubble"
        # Add padding inside the bubble
        padded_message = f" {message} \n"
        self.chat_display.insert(ctk.END, padded_message, bubble_tag)
        
        # Add spacing between messages
        self.chat_display.insert(ctk.END, "\n")
        
        self.chat_display.see(ctk.END)
        self.chat_display.configure(state="disabled")

    def handle_text_input(self, event=None):
        prompt = self.chat_entry.get()
        if prompt.strip():
            self.chat_entry.delete(0, ctk.END)
            self.update_chat_display("You", prompt)
            threading.Thread(
                target=self.run_chat_logic, args=(prompt,), daemon=True
            ).start()

    def handle_mic_input(self):
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()

    def _set_mic_button_state(self, active: bool):
        text = "⏹" if active else "🎙️"
        fg_color = ("#E53935", "#D32F2F") if active else ("#0078D4", "#0066B8")
        hover_color = ("#C62828", "#B71C1C") if active else ("#005A9E", "#0078D4")
        self.mic_button.configure(
            text=text, fg_color=fg_color, hover_color=hover_color
        )

    def start_listening(self):
        if self.stt_worker_active:
            return
        self.listening = True
        self.stt_worker_active = True
        self.mic_stop_event.clear()
        self._clear_audio_queue()
        self.wave_bubble.reset()
        self.wave_bubble.grid(row=0, column=1, padx=10)
        self.wave_bubble.set_active(True)
        self._set_mic_button_state(True)
        self.set_all_indicators("inactive")
        self.status_label.configure(
            text="🎤 Listening...",
            text_color=("#0078D4", "#4A9FFF")
        )
        self.stt_indicator.set_state("active")
        self.mic_thread = threading.Thread(target=self.run_mic_logic, daemon=True)
        self.mic_thread.start()

    def stop_listening(self):
        if not self.listening:
            return
        self.listening = False
        self.mic_stop_event.set()
        self.wave_bubble.set_active(False)
        self.wave_bubble.grid_remove()
        self._set_mic_button_state(False)
        if self.stt_worker_active:
            self.status_label.configure(
                text="⏹ Processing...",
                text_color=("#FF9800", "#FFB74D")
            )

    def run_mic_logic(self):
        future = asyncio.run_coroutine_threadsafe(
            codes.stt_handler.listen_and_transcribe(
                self.audio_queue, stop_event=self.mic_stop_event
            ),
            self.async_loop,
        )

        try:
            prompt = future.result()
        except Exception as exc:
            print(f"[STT] Error while transcribing: {exc}")
            prompt = ""

        self.after(0, lambda: self._handle_stt_completion(prompt))

    def run_chat_logic(self, prompt):
        self._safe_ui(
            self.status_label.configure,
            text="💭 Thinking...",
            text_color=("#6C3BA6", "#B084E0")
        )
        self._safe_ui(self.llm_indicator.set_state, "active")

        future = asyncio.run_coroutine_threadsafe(
            codes.llm_handler.query_llm(prompt), self.async_loop
        )
        try:
            response_text, provider = future.result()
        except Exception as exc:
            print(f"[LLM] Error: {exc}")
            response_text = "I'm still thinking, could you try asking again in a moment?"
            provider = "Unavailable"

        self._safe_ui(self.llm_indicator.set_state, "success")
        self._safe_ui(self.provider_label.configure, text=f"🤖 {provider}")
        self._safe_ui(self.update_chat_display, "Sophia", response_text)

        if self.tts_enabled:
            self._safe_ui(
                self.status_label.configure,
                text="🔊 Speaking...",
                text_color=("#4CAF50", "#66BB6A")
            )
            self._safe_ui(self.tts_indicator.set_state, "active")

            tts_future = asyncio.run_coroutine_threadsafe(
                codes.tts_handler.speak_text(response_text), self.async_loop
            )
            try:
                tts_future.result()
            except Exception as exc:
                print(f"[TTS] Error: {exc}")

            self._safe_ui(self.tts_indicator.set_state, "success")

        self._safe_ui(
            self.status_label.configure,
            text="✨ Ready",
            text_color=("#666666", "#999999")
        )

    def set_all_indicators(self, state):
        self.stt_indicator.set_state(state)
        self.llm_indicator.set_state(state)
        self.tts_indicator.set_state(state)

    def _handle_stt_completion(self, prompt: str):
        self.stt_worker_active = False
        self.listening = False
        self.mic_stop_event.set()
        self.wave_bubble.set_active(False)
        self.wave_bubble.grid_remove()
        self._set_mic_button_state(False)
        self.stt_indicator.set_state("success" if prompt else "inactive")
        self.status_label.configure(
            text="✨ Ready",
            text_color=("#666666", "#999999")
        )

        if prompt:
            if prompt.startswith("Error:"):
                self.update_chat_display("Sophia", prompt)
            else:
                self.update_chat_display("You", prompt)
                threading.Thread(
                    target=self.run_chat_logic, args=(prompt,), daemon=True
                ).start()

    def _clear_audio_queue(self):
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def _update_waveform(self):
        latest_amplitude = None
        while not self.audio_queue.empty():
            try:
                latest_amplitude = self.audio_queue.get_nowait()
            except queue.Empty:
                break

        if latest_amplitude is not None:
            normalized = min(latest_amplitude * 14, 1.0)
            self.wave_bubble.push_sample(normalized)
        else:
            decay = 0.03 if self.listening else 0.08
            self.wave_bubble.decay(decay)

        self.wave_bubble.set_active(self.listening)
        self.after(70, self._update_waveform)

    def on_closing(self):
        self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        self.destroy()
