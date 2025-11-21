import asyncio
import threading
import time
import math
import random
import queue
from typing import Optional

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageFilter, ImageGrab, ImageTk

try:
    import codes.llm_handler
    import codes.stt_handler
    import codes.tts_handler
except ImportError:
    print("Warning: 'codes' modules not found. Ensure project structure is correct.")

UI_COLORS = {
    "overlay_dim": "#000000",
    "card_bg": "#0A0A0A",
    "canvas_bg": "#0A0A0A",
    "glass_border_idle": "#2A2A2A",
    "glass_border_active": "#00D9FF",
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0A0A0",
    "accent_blue": "#00D9FF",
    "accent_red": "#FF3366",
    "accent_purple": "#A855F7",
    "accent_yellow": "#FFCC00",
    "accent_green": "#00E676",
    "orbiter_fill": "#00D9FF",
    "sphere_glow": "#00D9FF22",
}

FONTS = {
    "header": ("Roboto", 14, "bold"),
    "status": ("Roboto", 12),
    "subtitles": ("Roboto", 16),
    "icon": ("Segoe UI Emoji", 20),
}

class AISphere(tk.Frame):
    def __init__(self, parent, width=300, height=300, particle_count=250):
        bg_color = UI_COLORS["canvas_bg"]
        super().__init__(parent, bg=bg_color, highlightthickness=0, bd=0)
        self.width = width
        self.height = height
        
        self.canvas = tk.Canvas(
            self, 
            width=width, 
            height=height, 
            bg=bg_color,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.particles = []
        self.base_radius = min(width, height) / 3.2
        self.angle_y = 0
        self.angle_x = 0
        self.amplitude = 0.0
        self.breathing_phase = 0.0
        self.running = False
        self.active = False
        
        self._init_sphere_points(count=int(particle_count * 0.65))
        self._init_ring_points(count=int(particle_count * 0.35))

    def _init_sphere_points(self, count):
        phi = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(count):
            y = 1 - (i / float(count - 1)) * 2
            radius = math.sqrt(1 - y * y)
            theta = phi * i

            x = math.cos(theta) * radius
            z = math.sin(theta) * radius
            
            layer = random.choice([0.8, 1.0, 1.2]) 
            
            self.particles.append({
                "x": x * layer, "y": y * layer, "z": z * layer, 
                "type": "core", 
                "base_size": random.uniform(1.2, 2.8),
                "pulse_offset": random.uniform(0, math.pi)
            })

    def _init_ring_points(self, count):
        for i in range(count):
            theta = (i / count) * 2 * math.pi
            tilt = 0.3
            r = 1.4
            
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            y = math.sin(theta * 3) * 0.1
            
            y_tilted = y * math.cos(tilt) - z * math.sin(tilt)
            z_tilted = y * math.sin(tilt) + z * math.cos(tilt)
            
            self.particles.append({
                "x": x, "y": y_tilted, "z": z_tilted, 
                "type": "ring", 
                "base_size": random.uniform(0.8, 1.8),
                "pulse_offset": 0
            })

    def set_active(self, is_active: bool):
        self.active = is_active
        if is_active and not self.running:
            self.running = True
            self._animate()
        elif not is_active:
            self.running = False
            self.amplitude = 0.0
            self.canvas.delete("all")

    def set_amplitude(self, amplitude: float):
        amplitude = max(0.0, min(1.0, amplitude))
        target = amplitude * 0.8
        self.amplitude = self.amplitude * 0.7 + target * 0.3

    def _animate(self):
        if not self.winfo_exists() or not self.running:
            self.running = False
            return

        try:
            self.canvas.delete("all")
        except:
            self.running = False
            return
        cx, cy = self.width / 2, self.height / 2
        
        speed_mult = 1.0 + (self.amplitude * 3.0)
        self.angle_y += 0.02 * speed_mult
        self.angle_x += 0.005 * math.sin(self.breathing_phase * 0.5)
        
        self.breathing_phase += 0.05
        breathing_effect = math.sin(self.breathing_phase) * 0.08
        
        if self.amplitude > 0.01:
            current_pulse = 1.0 + (self.amplitude * 0.4)
        else:
            current_pulse = 1.0 + breathing_effect
        
        g1_r = self.base_radius * 2.2 * current_pulse
        self.canvas.create_oval(
            cx - g1_r, cy - g1_r, cx + g1_r, cy + g1_r,
            fill="#050a14", outline="", tags="glow"
        )
        
        g2_r = self.base_radius * 1.4 * current_pulse
        mix = min(1.0, self.amplitude * 1.5)
        gr = int(0 + 48 * mix)
        gg = int(16 - 16 * mix)
        gb = int(48 + 0 * mix)
        glow_hex = f"#{gr:02x}{gg:02x}{gb:02x}"
        
        self.canvas.create_oval(
            cx - g2_r, cy - g2_r, cx + g2_r, cy + g2_r,
            fill=glow_hex, outline="", tags="glow"
        )

        cos_y, sin_y = math.cos(self.angle_y), math.sin(self.angle_y)
        cos_x, sin_x = math.cos(self.angle_x), math.sin(self.angle_x)

        projected_particles = []

        for p in self.particles:
            x = p["x"] * cos_y - p["z"] * sin_y
            z = p["z"] * cos_y + p["x"] * sin_y
            y = p["y"]
            
            y_new = y * cos_x - z * sin_x
            z_new = z * cos_x + y * sin_x
            x_new = x
            
            if p["type"] == "core":
                indiv_pulse = 1.0 + 0.1 * math.sin(self.breathing_phase + p["pulse_offset"])
                scale_factor = current_pulse * indiv_pulse
            else:
                scale_factor = 1.0 + (self.amplitude * 0.1)
                
            x_final = x_new * self.base_radius * scale_factor
            y_final = y_new * self.base_radius * scale_factor
            z_final = z_new * self.base_radius * scale_factor

            scale = 300 / (400 + z_final)
            px = cx + x_final * scale
            py = cy + y_final * scale
            
            projected_particles.append({
                "x": px, "y": py, "z": z_final, 
                "type": p["type"], "base_size": p["base_size"]
            })

        projected_particles.sort(key=lambda p: p["z"])

        r_base, g_base, b_base = 0, 217, 255    # Brighter cyan
        r_peak, g_peak, b_peak = 168, 85, 247   # Purple instead of red
        
        r = int(r_base * (1 - mix) + r_peak * mix)
        g = int(g_base * (1 - mix) + g_peak * mix)
        b = int(b_base * (1 - mix) + b_peak * mix)
        dynamic_color = f"#{r:02x}{g:02x}{b:02x}"

        front_particles = [p for p in projected_particles if p["z"] > 0 and p["type"] == "core"]
        
        if len(front_particles) > 0:
            for i, p1 in enumerate(front_particles):
                if i % 2 != 0: continue
                
                closest_dist = 9999
                closest_p = None
                
                for p2 in front_particles[i+1:i+10]:
                    dx = p1["x"] - p2["x"]
                    dy = p1["y"] - p2["y"]
                    dist_sq = dx*dx + dy*dy
                    if dist_sq < closest_dist:
                        closest_dist = dist_sq
                        closest_p = p2
                
                if closest_p and closest_dist < 2500:
                    alpha = 1.0 - (closest_dist / 2500)
                    if alpha > 0.3:
                        line_col = dynamic_color if alpha > 0.7 else f"#{int(r*0.4):02x}{int(g*0.4):02x}{int(b*0.6):02x}"
                        self.canvas.create_line(
                            p1["x"], p1["y"], closest_p["x"], closest_p["y"],
                            fill=line_col, width=1, tags="conn"
                        )

        for p in projected_particles:
            depth = (p["z"] + self.base_radius) / (2 * self.base_radius)
            depth = max(0.2, min(1.0, depth))
            
            size = p["base_size"] * (0.4 + depth * 0.8)
            
            if p["type"] == "core":
                if depth > 0.85: 
                    color = "#FFFFFF"
                elif depth > 0.5: 
                    color = dynamic_color
                else: 
                    color = f"#{int(r*0.2):02x}{int(g*0.2):02x}{int(b*0.4):02x}"
            else:
                if depth > 0.5:
                    color = dynamic_color
                else:
                    color = "#1a2a3a"

            self.canvas.create_oval(
                p["x"] - size, p["y"] - size,
                p["x"] + size, p["y"] + size,
                fill=color, outline=""
            )

        if self.running and self.active:
            self.after(20, self._animate)


class VoiceMode:
    def __init__(self, parent, async_loop, audio_queue: queue.Queue, mic_stop_event):
        print("[VoiceMode] Initializing...")
        self.parent = parent
        self.async_loop = async_loop
        self.audio_queue = audio_queue
        self.mic_stop_event = mic_stop_event

        self.popup_listening = False
        self.stt_worker_active = False
        self.listening = False
        self.current_state = "idle"
        self.auto_listen_active = False

        self._pulse_active = False
        self._orbit_active = False
        self._wave_active = False
        self._drag_data = {"x": 0, "y": 0}
        self._blur_image_ref = None
        self._blur_label = None

        self._create_popup()
        self._bind_keyboard_shortcuts()
        print("[VoiceMode] Initialization complete.")

    def _create_popup(self):
        print("[VoiceMode] Creating popup UI...")
        
        self.voice_overlay = tk.Frame(self.parent, bg=UI_COLORS["overlay_dim"])
        self.voice_overlay.place_forget()

        self._setup_blur_background()

        self.voice_popup = ctk.CTkFrame(
            master=self.voice_overlay,
            width=440, height=680,
            fg_color=UI_COLORS["card_bg"],
            corner_radius=28,
            border_width=2,
            border_color=UI_COLORS["glass_border_idle"],
        )
        self.voice_popup.place(relx=0.5, rely=0.5, anchor="center")

        self.voice_popup.bind("<ButtonPress-1>", self._on_card_press)
        self.voice_popup.bind("<B1-Motion>", self._on_card_move)

        self._create_header()

        self.visual_canvas = tk.Canvas(
            self.voice_popup, 
            width=380, height=380, 
            bg=UI_COLORS["canvas_bg"],
            highlightthickness=0
        )
        self.visual_canvas.pack(pady=10)
        
        self.visual_canvas.bind("<ButtonPress-1>", self._on_card_press)
        self.visual_canvas.bind("<B1-Motion>", self._on_card_move)

        cx, cy = 190, 190
        
        self.halo_radius = 150
        self.halo_id = self.visual_canvas.create_oval(
            cx - self.halo_radius, cy - self.halo_radius,
            cx + self.halo_radius, cy + self.halo_radius,
            outline=UI_COLORS["glass_border_idle"], width=2
        )

        sphere_holder = tk.Frame(self.visual_canvas, width=260, height=260, bg=UI_COLORS["canvas_bg"])
        self.visual_canvas.create_window(cx, cy, window=sphere_holder)
        
        try:
            self.popup_sphere = AISphere(sphere_holder, width=260, height=260, particle_count=240)
            self.popup_sphere.pack()
        except NameError:
            tk.Label(sphere_holder, text="[Sphere]", bg=UI_COLORS["canvas_bg"], fg="white").pack()
            self.popup_sphere = type('obj', (object,), {'set_active': lambda s, x: None, 'set_amplitude': lambda s, x: None})()

        self._orbiters = []
        self._create_orbiters(n=4, radius=self.halo_radius + 20, center=(cx, cy))
        self._create_orbiters(n=6, radius=self.halo_radius - 15, center=(cx, cy))

        self._wave_bars = []
        self._wave_bar_count = 32
        self._init_waveform(cx, 360)

        self._create_status_bar()

    def _setup_blur_background(self):
        """Attempts to grab screen for blur, fails gracefully to dark overlay."""
        # Clean up old blur label if it exists
        if hasattr(self, "_blur_label") and self._blur_label:
            try:
                self._blur_label.destroy()
            except Exception:
                pass
            self._blur_label = None

        try:
            # Check if window is visible before grabbing
            if self.parent.winfo_viewable():
                x = self.parent.winfo_rootx()
                y = self.parent.winfo_rooty()
                w = self.parent.winfo_width()
                h = self.parent.winfo_height()
                
                # Only grab if dimensions are sane
                if w > 100 and h > 100:
                    img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
                    # Apply dark tint and blur
                    blurred = img.filter(ImageFilter.GaussianBlur(radius=20)).point(lambda p: p * 0.4)
                    self._blur_image_ref = ImageTk.PhotoImage(blurred)
                    
                    self._blur_label = tk.Label(self.voice_overlay, image=self._blur_image_ref, bg="black")
                    self._blur_label.place(relx=0, rely=0, relwidth=1, relheight=1)
                    # Ensure blur is behind everything else
                    self._blur_label.lower()
                    return
        except Exception as e:
            print(f"[UI] Background blur disabled (Normal): {e}")
        
        # Fallback color
        self.voice_overlay.configure(bg="#050505")

    def _create_header(self):
        header = ctk.CTkFrame(self.voice_popup, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 8))
        
        # Title with icon
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame, text="✨", 
            font=("Segoe UI Emoji", 18)
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(
            title_frame, text="SOPHIA", 
            font=("Segoe UI", 16, "bold"), 
            text_color=UI_COLORS["accent_blue"]
        ).pack(side="left")
        
        ctk.CTkLabel(
            title_frame, text="AI", 
            font=("Segoe UI", 16, "bold"), 
            text_color=UI_COLORS["text_secondary"]
        ).pack(side="left", padx=(4, 0))
        
        close_btn = ctk.CTkButton(
            header, text="✕", width=36, height=36, 
            fg_color="#1A1A1A", 
            hover_color=UI_COLORS["accent_red"], 
            text_color=UI_COLORS["text_secondary"],
            font=("Arial", 16, "bold"),
            corner_radius=18,
            border_width=1,
            border_color=UI_COLORS["glass_border_idle"],
            command=self.hide
        )
        close_btn.pack(side="right")

    def _create_status_bar(self):
        status_frame = ctk.CTkFrame(
            self.voice_popup, 
            fg_color="#151515",
            corner_radius=20,
            height=48
        )
        status_frame.pack(pady=(0, 18), padx=20, fill="x")
        status_frame.pack_propagate(False)
        
        inner_frame = ctk.CTkFrame(status_frame, fg_color="transparent")
        inner_frame.pack(expand=True)
        
        self.state_icon = ctk.CTkLabel(inner_frame, text="💤", font=FONTS["icon"])
        self.state_icon.pack(side="left", padx=(0, 10))
        
        self.popup_status = ctk.CTkLabel(
            inner_frame, text="Ready", 
            font=("Segoe UI", 13, "bold"), 
            text_color=UI_COLORS["text_secondary"]
        )
        self.popup_status.pack(side="left")

        self.transcription_label = ctk.CTkLabel(
            self.voice_popup, text="", 
            font=("Segoe UI", 15), 
            text_color=UI_COLORS["text_primary"], 
            wraplength=400, justify="center"
        )
        self.transcription_label.pack(side="bottom", pady=(0, 48), padx=24)

    # ---------------------------
    # Visuals: Orbiters & Waveform
    # ---------------------------
    def _create_orbiters(self, n=6, radius=110, center=(170, 150)):
        cx, cy = center
        for i in range(n):
            angle = 2 * math.pi * i / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            r = 5 # Slightly smaller particles
            # Use a brighter fill for contrast against dark bg
            orb = self.visual_canvas.create_oval(x - r, y - r, x + r, y + r, fill=UI_COLORS["orbiter_fill"], outline="")
            self._orbiters.append({"id": orb, "angle": angle, "dist": radius, "speed": 0.02 + (i % 3) * 0.007})

    def _orbit_step(self):
        if not self._orbit_active: return
        
        cx, cy = 190, 190
        for o in self._orbiters:
            o["angle"] += o["speed"]
            # Add a slight vertical oscillation for organic feel
            wobble = 0.05 * math.sin(o["angle"] * 3)
            
            x = cx + o["dist"] * math.cos(o["angle"])
            y = cy + o["dist"] * math.sin(o["angle"] * (1 + wobble))
            self.visual_canvas.coords(o["id"], x - 5, y - 5, x + 5, y + 5)
            
        self.parent.after(28, self._orbit_step)

    def _init_waveform(self, x_center, y_base):
        width = 280
        bar_w = width / self._wave_bar_count
        start_x = x_center - width / 2
        for i in range(self._wave_bar_count):
            x1 = start_x + i * bar_w + 2
            x2 = x1 + bar_w - 2
            h = 4
            # Use accent blue
            rect = self.visual_canvas.create_rectangle(
                x1, y_base - h, x2, y_base + h, 
                fill=UI_COLORS["accent_blue"], outline=""
            )
            self._wave_bars.append(rect)

    def _wave_step(self):
        if not self._wave_active: return

        amps = []
        # Drain queue to get latest data, but cap it
        try:
            while not self.audio_queue.empty() and len(amps) < 10:
                amps.append(self.audio_queue.get_nowait())
        except queue.Empty:
            pass

        # Create organic idle movement if no audio
        if not amps:
            t = time.time()
            amps = [0.05 + 0.03 * math.sin(t * 3 + i * 0.5) for i in range(self._wave_bar_count)]

        max_val = max(max(amps), 0.001)
        
        for i, bar in enumerate(self._wave_bars):
            # Index wrapping
            val = amps[i % len(amps)]
            
            # Scale height based on audio (logarithmic scaling feels more natural)
            normalized = val / max_val
            height = 4 + (normalized * 40)
            
            coords = self.visual_canvas.coords(bar)
            if coords:
                x1, _, x2, _ = coords
                mid_y = 360
                self.visual_canvas.coords(bar, x1, mid_y - height, x2, mid_y + height)
                
                # Gradient color based on intensity
                if height < 15:
                    color = UI_COLORS["accent_blue"]
                elif height < 30:
                    color = UI_COLORS["accent_purple"]
                else:
                    color = "#FF3366"  # Vibrant pink for peaks
                self.visual_canvas.itemconfigure(bar, fill=color)

        self.parent.after(50, self._wave_step)

    # ---------------------------
    # Interaction: Dragging
    # ---------------------------
    def _on_card_press(self, event):
        self._drag_data["x"] = event.x_root - self.voice_popup.winfo_rootx()
        self._drag_data["y"] = event.y_root - self.voice_popup.winfo_rooty()

    def _on_card_move(self, event):
        new_x = event.x_root - self._drag_data["x"]
        new_y = event.y_root - self._drag_data["y"]
        
        # Calculate relative position to keep popup within parent bounds
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        # Convert to relative coordinates (0.0 - 1.0)
        relx = (new_x - self.parent.winfo_rootx()) / parent_w
        rely = (new_y - self.parent.winfo_rooty()) / parent_h
        
        # Clamp to keep partially on screen
        relx = max(0.05, min(0.95, relx))
        rely = max(0.05, min(0.95, rely))
        
        self.voice_popup.place_configure(relx=relx, rely=rely, anchor="center")

    # ---------------------------
    # Logic: Visibility & State
    # ---------------------------
    def _bind_keyboard_shortcuts(self):
        self.parent.bind("<Escape>", lambda e: self.hide())
        self.parent.bind("<Control-m>", lambda e: self.toggle_auto_listen())

    def show(self):
        print("[VoiceMode] show() called.")
        # Re-grab blur if possible for fresh background
        self._setup_blur_background()
        
        self.voice_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.voice_overlay.lift()
        
        # Ensure popup is always on top of the blur layer
        if hasattr(self, "voice_popup"):
            self.voice_popup.lift()
            
        print("[VoiceMode] Overlay placed and lifted.")
        
        self._orbit_active = True
        self._wave_active = True
        self._orbit_step()
        self._wave_step()
        
        self.popup_sphere.set_active(True)
        self.auto_listen_active = True
        self._set_state("idle")
        
        self.parent.after(200, self._start_auto_listening)

    def hide(self):
        self.auto_listen_active = False
        self.stop_listening()
        
        self._orbit_active = False
        self._wave_active = False
        self.popup_sphere.set_active(False)
        
        self.voice_overlay.place_forget()

    def toggle_auto_listen(self):
        if not self.voice_overlay.winfo_ismapped():
            self.show()
            return

        self.auto_listen_active = not self.auto_listen_active
        if self.auto_listen_active:
            self._set_state("idle")
            self._start_auto_listening()
        else:
            self.stop_listening()
            self._set_state("idle")

    def _set_state(self, state: str):
        self.current_state = state
        
        # Configuration mapping: (Icon, Border Color, Text, Text Color)
        cfg = {
            "idle": ("💤", UI_COLORS["glass_border_idle"], "Ready to listen", UI_COLORS["text_secondary"]),
            "listening": ("🎙️", UI_COLORS["accent_red"], "Listening...", UI_COLORS["accent_red"]),
            "processing": ("✨", UI_COLORS["accent_yellow"], "Thinking...", UI_COLORS["accent_yellow"]),
            "speaking": ("🔊", UI_COLORS["accent_purple"], "Speaking...", UI_COLORS["accent_purple"]),
        }
        
        icon, color, text, text_color = cfg.get(state, cfg["idle"])
        
        self._safe_ui_update(self.state_icon.configure, text=icon)
        self._safe_ui_update(self.popup_status.configure, text=text, text_color=text_color)
        self._safe_ui_update(self.voice_popup.configure, border_color=color)
        self._safe_ui_update(self.visual_canvas.itemconfigure, self.halo_id, outline=color)

        # Pulse animation logic
        if state == "listening":
            self._start_pulse_animation()
        else:
            self._stop_pulse_animation()

    # ---------------------------
    # Microphone & Processing Logic
    # ---------------------------
    def _start_auto_listening(self):
        if self.auto_listen_active and not self.stt_worker_active:
            self.start_listening()

    def start_listening(self):
        if self.stt_worker_active: return
        
        self.popup_listening = True
        self.stt_worker_active = True
        self.mic_stop_event.clear()
        
        # Clear old audio data
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
            
        self._set_state("listening")
        threading.Thread(target=self._run_mic_logic, daemon=True).start()

    def stop_listening(self):
        if self.popup_listening:
            self.popup_listening = False
            self.mic_stop_event.set()
            self._set_state("processing")

    def _run_mic_logic(self):
        """Threaded wrapper for STT."""
        def on_partial(text):
            if text:
                # Only animate new words to prevent jitter
                self._safe_ui_update(self._show_floating_subtitle, text + "...")

        def on_final(text):
            if text:
                self._safe_ui_update(self.transcription_label.configure, text=text)

        prompt = ""
        try:
            # Bridge to async world
            future = asyncio.run_coroutine_threadsafe(
                codes.stt_handler.whisper_streaming_advanced(
                    amplitude_queue=self.audio_queue,
                    stop_event=self.mic_stop_event,
                    partial_callback=on_partial,
                    final_callback=on_final
                ), 
                self.async_loop
            )
            prompt = future.result()
        except Exception as e:
            print(f"[STT] Error: {e}")

        self.parent.after(0, lambda: self._handle_stt_result(prompt))

    def _handle_stt_result(self, prompt):
        self.stt_worker_active = False
        self.popup_listening = False
        
        if prompt:
            print(f"[STT] Recognized: {prompt}")
            self._set_state("processing")
            threading.Thread(target=self._run_llm_logic, args=(prompt,), daemon=True).start()
        else:
            self._set_state("idle")
            if self.auto_listen_active:
                self.parent.after(500, self._start_auto_listening)

    # ---------------------------
    # LLM & TTS Logic
    # ---------------------------
    def _run_llm_logic(self, prompt):
        buffer = ""
        import re
        
        def on_stream(text):
            nonlocal buffer
            buffer += text
            # Split by sentence endings (. ! ? \n) followed by space or end of string
            # We use a lookbehind to keep the punctuation
            parts = re.split(r'(?<=[.!?\n])\s+', buffer)
            
            if len(parts) > 1:
                # We have at least one complete sentence
                for part in parts[:-1]:
                    if part.strip():
                        self._set_state("speaking")
                        self._speak_chunk(part.strip())
                # Keep the last part (incomplete sentence)
                buffer = parts[-1]

        try:
            future = asyncio.run_coroutine_threadsafe(
                codes.llm_handler.query_llm(prompt, stream_callback=on_stream),
                self.async_loop
            )
            full_response, _ = future.result()
            
            # Speak remaining text
            if buffer.strip():
                self._speak_chunk(buffer.strip())
                
        except Exception as e:
            print(f"[LLM] Error: {e}")
            
        # Finished
        self._safe_ui_update(self.transcription_label.configure, text="")
        
        # Callback to restart listening ONLY after audio finishes
        def on_speech_done():
            self._safe_ui_update(self._set_state, "idle")
            if self.auto_listen_active:
                # Small delay to ensure mic doesn't catch echo
                self.parent.after(500, lambda: self._safe_ui_update(self._start_auto_listening))

        # Send empty chunk to trigger callback after all audio is played
        self._speak_chunk("", on_finish=on_speech_done)

    def _speak_chunk(self, text, on_finish=None):
        """Invokes TTS and updates visuals."""
        def amp_cb(a):
            self._safe_ui_update(self.popup_sphere.set_amplitude, a)

        try:
            # Fire and forget (TTS queue handles serialization)
            asyncio.run_coroutine_threadsafe(
                codes.tts_handler.speak_text_streaming(text, amplitude_callback=amp_cb, on_complete=on_finish),
                self.async_loop
            )
        except Exception:
            pass

    def _show_floating_subtitle(self, text, duration_ms=1500):
        """Animates text floating up from the bottom."""
        lbl = tk.Label(
            self.voice_popup, text=text, 
            bg=UI_COLORS["card_bg"], fg=UI_COLORS["text_primary"], 
            font=("Roboto", 12, "italic")
        )
        lbl.place(relx=0.5, rely=0.85, anchor="center")
        
        start_t = time.time()
        
        def animate():
            elapsed = (time.time() - start_t) * 1000
            progress = min(1.0, elapsed / duration_ms)
            
            # Move Up
            new_y = 0.85 - (0.05 * progress)
            lbl.place_configure(rely=new_y)
            
            # Fake Alpha (Darken text to fade out)
            if progress > 0.5:
                fade_p = (progress - 0.5) * 2
                # Interpolate White -> Card BG
                gray_val = int(255 * (1 - fade_p) + 19 * fade_p) # 19 is approx hex 13
                hex_col = f"#{gray_val:02x}{gray_val:02x}{gray_val:02x}"
                lbl.configure(fg=hex_col)

            if progress < 1.0:
                self.parent.after(30, animate)
            else:
                lbl.destroy()
        
        animate()

    def _start_pulse_animation(self):
        if self._pulse_active: return
        self._pulse_active = True
        self._pulse_tick = 0
        
        def loop():
            if not self._pulse_active: 
                self.visual_canvas.itemconfigure(self.halo_id, width=2)
                return
                
            # Sin wave for width
            w = 2 + 2 * math.sin(self._pulse_tick * 0.2)
            w = max(1, w) # clamp
            self.visual_canvas.itemconfigure(self.halo_id, width=w)
            self._pulse_tick += 1
            self.parent.after(50, loop)
            
        loop()

    def _stop_pulse_animation(self):
        self._pulse_active = False

    def _safe_ui_update(self, func, *args, **kwargs):
        """Thread-safe UI update helper."""
        if threading.current_thread() is threading.main_thread():
            try:
                func(*args, **kwargs)
            except Exception:
                pass
        else:
            self.parent.after(0, lambda: self._safe_ui_update(func, *args, **kwargs))