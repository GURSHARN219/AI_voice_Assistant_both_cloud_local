import customtkinter as ctk
import threading
import asyncio
import queue

import codes.llm_handler
import codes.stt_handler
import codes.tts_handler


class Indicator:
    """A visual indicator for processing steps (STT, LLM, TTS)."""

    def __init__(self, parent, text):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.label = ctk.CTkLabel(
            self.frame, text=text, font=("Roboto", 12, "bold"), text_color="#7A7A7A"
        )
        self.label.pack(side="left")
        self.dot = ctk.CTkLabel(
            self.frame, text="●", font=("Arial", 16), text_color="#4A4A4A"
        )
        self.dot.pack(side="left", padx=4)

    def set_state(self, state: str):
        """Sets the indicator state ('inactive', 'active', 'success')."""
        colors = {"inactive": "#4A4A4A", "active": "#F39C12", "success": "#2ECC71"}
        self.dot.configure(text_color=colors.get(state, "#4A4A4A"))

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


class VoiceChatGUI(ctk.CTk):
    """The main GUI class for the AI Chatbot application."""

    def __init__(self, loop):
        super().__init__()
        self.async_loop = loop
        self.audio_queue = queue.Queue()
        self.tts_enabled = True  # TTS is on by default

        self.title("Sophia AI Assistant")
        self.iconbitmap("aura.ico")

        # photo = tk.PhotoImage(file='path/to/your/my_icon.png')
        # self.wm_iconphoto(False, photo)

        self.geometry("700x650")
        ctk.set_appearance_mode("dark")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Create UI Panels ---
        self._create_chat_panel()
        self._create_status_bar()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(500, self.show_initial_greeting)

    def _create_chat_panel(self):
        """Creates the main chat panel that fills the window."""
        container_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        container_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        container_frame.grid_rowconfigure(0, weight=1)
        container_frame.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(
            container_frame,
            font=("Roboto", 16),
            corner_radius=10,
            border_width=2,
            fg_color="#1C1C1C",
            border_color="#333333",
            wrap="word",
            state="disabled",
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.tag_config("user", justify="right", rmargin=10)
        self.chat_display.tag_config("ai", justify="left", lmargin1=10, lmargin2=10)

        input_frame = ctk.CTkFrame(container_frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=0, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_entry = ctk.CTkEntry(
            input_frame, font=("Roboto", 14), placeholder_text="Ask Sophia anything..."
        )
        self.chat_entry.grid(row=0, column=0, sticky="ew", ipady=5)
        self.chat_entry.bind("<Return>", self.handle_text_input)

        mic_button = ctk.CTkButton(
            input_frame,
            text="🎙️",
            width=30,
            height=30,
            font=("Arial", 20),
            corner_radius=20,
            command=self.handle_mic_input,
            fg_color="#2B2B2B",
            hover_color="#3B3B3B",
        )
        mic_button.grid(row=0, column=1, padx=10)

    def _create_status_bar(self):
        """Creates the bottom status bar with an improved layout."""
        status_bar = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="#1F1F1F",
            border_width=1,
            border_color="#333333",
        )
        status_bar.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        status_bar.grid_rowconfigure(0, pad=5)
        status_bar.grid_columnconfigure(0, weight=1)
        status_bar.grid_columnconfigure(1, weight=0)
        status_bar.grid_columnconfigure(2, weight=1)

        # --- Left side: Status Label ---
        self.status_label = ctk.CTkLabel(
            status_bar, text="Status: Idle", font=("Roboto", 12)
        )
        self.status_label.grid(row=0, column=0, padx=15, sticky="w")

        # --- Center: Process Indicators ---
        indicator_frame = ctk.CTkFrame(status_bar, fg_color="transparent")
        indicator_frame.grid(
            row=0, column=1, sticky="ns"
        )  # Center the frame in the column

        self.stt_indicator = Indicator(indicator_frame, "STT")
        self.stt_indicator.pack(side="left", padx=5)
        self.llm_indicator = Indicator(indicator_frame, "LLM")
        self.llm_indicator.pack(side="left", padx=5)
        self.tts_indicator = Indicator(indicator_frame, "TTS")
        self.tts_indicator.pack(side="left", padx=5)

        # --- Right side: Provider and Buttons ---
        right_group = ctk.CTkFrame(status_bar, fg_color="transparent")
        right_group.grid(row=0, column=2, padx=15, sticky="e")

        button_fg_color = ("#F0F0F0", "#2B2B2B")
        button_hover_color = ("#E0E0E0", "#3B3B3B")

        # Pack order is right-to-left
        self.theme_button = ctk.CTkButton(
            right_group,
            text="🌙",
            width=25,
            height=25,
            font=("Arial", 16),
            corner_radius=5,
            command=self.toggle_theme,
            fg_color=button_fg_color,
            hover_color=button_hover_color,
        )
        self.theme_button.pack(side="right", padx=(10, 0))

        self.tts_button = ctk.CTkButton(
            right_group,
            text="🔊",
            width=25,
            height=25,
            font=("Arial", 16),
            corner_radius=5,
            command=self.toggle_tts,
            fg_color=button_fg_color,
            hover_color=button_hover_color,
        )
        self.tts_button.pack(side="right", padx=(10, 0))

        self.provider_label = ctk.CTkLabel(
            right_group, text="Provider: N/A", font=("Roboto", 12)
        )
        self.provider_label.pack(side="right")

    def toggle_theme(self):
        """Toggles the UI theme between light and dark mode."""
        current_mode = ctk.get_appearance_mode()
        new_mode = "light" if current_mode == "dark" else "dark"
        ctk.set_appearance_mode(new_mode)
        button_text = "☀️" if new_mode == "light" else "🌙"
        self.theme_button.configure(text=button_text)

    def toggle_tts(self):
        """Toggles the text-to-speech functionality on or off."""
        self.tts_enabled = not self.tts_enabled
        button_text = "🔊" if self.tts_enabled else "🔇"
        self.tts_button.configure(text=button_text)

    def show_initial_greeting(self):
        self.update_chat_display(
            "Sophia", "I'm Sophia, your AI assistant. How can I help you today?"
        )

    def update_chat_display(self, sender, message):
        self.chat_display.configure(state="normal")
        self.chat_display.insert(
            ctk.END, f"{sender}: {message}\n\n", "user" if sender == "You" else "ai"
        )
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
        threading.Thread(target=self.run_mic_logic, daemon=True).start()

    def run_mic_logic(self):
        self.set_all_indicators("inactive")
        self.status_label.configure(text="Status: Listening...")
        self.stt_indicator.set_state("active")

        future = asyncio.run_coroutine_threadsafe(
            codes.stt_handler.listen_and_transcribe(self.audio_queue), self.async_loop
        )
        prompt = future.result()

        self.stt_indicator.set_state("success" if prompt else "inactive")

        if prompt:
            self.update_chat_display("You", prompt)
            self.run_chat_logic(prompt)
        else:
            self.status_label.configure(text="Status: Idle")

    def run_chat_logic(self, prompt):
        self.status_label.configure(text="Status: Thinking...")
        self.llm_indicator.set_state("active")

        future = asyncio.run_coroutine_threadsafe(
            codes.llm_handler.query_llm(prompt), self.async_loop
        )
        response_text, provider = future.result()

        self.llm_indicator.set_state("success")
        self.provider_label.configure(text=f"Provider: {provider}")
        self.update_chat_display("Sophia", response_text)

        if self.tts_enabled:
            self.status_label.configure(text="Status: Speaking...")
            self.tts_indicator.set_state("active")

            tts_future = asyncio.run_coroutine_threadsafe(
                codes.tts_handler.speak_text(response_text), self.async_loop
            )
            tts_future.result()

            self.tts_indicator.set_state("success")

        self.status_label.configure(text="Status: Idle")

    def set_all_indicators(self, state):
        self.stt_indicator.set_state(state)
        self.llm_indicator.set_state(state)
        self.tts_indicator.set_state(state)

    def on_closing(self):
        self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        self.destroy()
