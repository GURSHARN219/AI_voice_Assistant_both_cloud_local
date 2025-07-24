import customtkinter as ctk
import numpy as np
import math
import time

# --- Constants ---
WAVEFORM_WIDTH = 300
WAVEFORM_HEIGHT = 60
SPHERE_SIZE = 220


class SphereVisualizer:
    """Handles drawing and animating a 3D wireframe sphere on a canvas."""

    def __init__(self, canvas: ctk.CTkCanvas):
        self.canvas = canvas
        self.is_active = False
        self.rotation_angle = 0
        self.points = self._generate_sphere_points()

    def _generate_sphere_points(self, num_points=200):
        """Generate points on a sphere using Fibonacci lattice."""
        points = []
        phi = math.pi * (3.0 - math.sqrt(5.0))  # Golden angle in radians
        for i in range(num_points):
            y = 1 - (i / float(num_points - 1)) * 2  # y goes from 1 to -1
            radius = math.sqrt(1 - y * y)
            theta = phi * i
            x = math.cos(theta) * radius
            z = math.sin(theta) * radius
            points.append((x, y, z))
        return points

    def start(self):
        if not self.is_active:
            self.is_active = True
            self._animate()

    def stop(self):
        self.is_active = False
        self.canvas.delete("all")

    def _animate(self):
        if not self.is_active:
            return
        self.canvas.delete("all")
        self.rotation_angle += 0.01

        center_x, center_y = SPHERE_SIZE / 2, SPHERE_SIZE / 2

        rotated_points = []
        for x, y, z in self.points:
            new_x = x * math.cos(self.rotation_angle) - z * math.sin(
                self.rotation_angle
            )
            new_z = x * math.sin(self.rotation_angle) + z * math.cos(
                self.rotation_angle
            )
            rotated_points.append((new_x, y, new_z))

        rotated_points.sort(key=lambda p: p[2])

        for x, y, z in rotated_points:
            screen_x = center_x + x * (SPHERE_SIZE / 2.5)
            screen_y = center_y + y * (SPHERE_SIZE / 2.5)
            size = (z + 2) * 1.5
            color_intensity = int((z + 1) / 2 * 200) + 55
            color = f"#{color_intensity:02x}{color_intensity:02x}{color_intensity:02x}"
            self.canvas.create_oval(
                screen_x - size,
                screen_y - size,
                screen_x + size,
                screen_y + size,
                fill=color,
                outline="",
            )

        self.canvas.after(20, self._animate)


class WaveformVisualizer:
    """Handles drawing the audio waveform on a canvas."""

    def __init__(self, canvas: ctk.CTkCanvas):
        self.canvas = canvas
        self.is_active = False
        self.mode = "idle"

    def set_mode(self, mode: str):
        self.mode = mode
        if self.mode != "idle" and not self.is_active:
            self.is_active = True
            if self.mode == "processing":
                self._animate_processing()
        elif self.mode == "idle":
            self.is_active = False
            self._draw_idle_line()

    def _draw_idle_line(self):
        self.canvas.delete("all")
        y = WAVEFORM_HEIGHT / 2
        self.canvas.create_line(
            0, y, WAVEFORM_WIDTH, y, fill="#4A4A4A", width=2, dash=(2, 4)
        )

    def update_listening_waveform(self, amplitude):
        if not self.is_active or self.mode != "listening":
            return
        self.canvas.delete("all")
        scaled_amplitude = min(amplitude * 7, WAVEFORM_HEIGHT / 1.5)
        x = np.linspace(0, WAVEFORM_WIDTH, WAVEFORM_WIDTH)
        y_offset = np.sin(x / 20) * 5
        y = (
            WAVEFORM_HEIGHT / 2
            + (scaled_amplitude / 2)
            * np.sin(x / 10)
            * np.exp(-((x - WAVEFORM_WIDTH / 2) ** 2) / (2 * (WAVEFORM_WIDTH / 4) ** 2))
            + y_offset
        )
        points = [(x[i], y[i]) for i in range(len(x))]
        self.canvas.create_line(points, fill="#3498DB", width=2, smooth=True)

    def _animate_processing(self):
        if not self.is_active or self.mode != "processing":
            return
        self.canvas.delete("all")
        amplitude = np.random.uniform(0.2, 0.8) * (WAVEFORM_HEIGHT / 2)
        frequency = np.random.uniform(0.8, 1.2)
        x = np.linspace(0, WAVEFORM_WIDTH, WAVEFORM_WIDTH)
        y = WAVEFORM_HEIGHT / 2 + amplitude * np.sin(
            2 * np.pi * frequency * (x / WAVEFORM_WIDTH) + time.time() * 5
        )
        points = [(x[i], y[i]) for i in range(len(x))]
        self.canvas.create_line(points, fill="#2ECC71", width=2, smooth=True)
        self.canvas.after(50, self._animate_processing)
