"""Floating, borderless, always-on-top three-button window.

Buttons: Record, Stop, AI Optimize. A status line shows the current state and
a small text area previews the draft / optimized text. The window is draggable
since it has no title bar.

All backend work is delegated to ``Controller``; callbacks from the controller
arrive on worker threads, so we marshal UI updates back onto the Tk main loop
with ``after``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from ..config import CONFIG
from ..controller import Controller, t

# Simple dark palette
BG = "#1e1f26"
FG = "#e6e6e6"
MUTED = "#9aa0b4"
ACCENT = "#5b8cff"
REC = "#ff5b6e"
BTN_BG = "#2a2c37"
BTN_ACTIVE = "#3a3d4d"


class FloatingWindow:
    def __init__(self, controller: Controller | None = None):
        self.cfg = CONFIG.ui
        self.controller = controller or Controller(lang=self.cfg.language)

        self.root = tk.Tk()
        self.root.title(self.cfg.title)
        self.root.configure(bg=BG)
        if self.cfg.borderless:
            self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.cfg.topmost)
        self.root.geometry("320x210+120+120")
        self.root.minsize(300, 200)

        self._drag = {"x": 0, "y": 0}
        self._build()
        self._wire_controller()
        self._set_state("idle")

    # -- construction --------------------------------------------------------
    def _build(self) -> None:
        title_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        btn_font = tkfont.Font(family="Helvetica", size=11)
        status_font = tkfont.Font(family="Helvetica", size=9)

        # Title bar (drag handle + close)
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=8, pady=(8, 0))
        title = tk.Label(bar, text=self.cfg.title, bg=BG, fg=MUTED, font=title_font)
        title.pack(side="left")
        close = tk.Label(bar, text="✕", bg=BG, fg=MUTED, cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.root.destroy())
        for w in (bar, title):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        # Buttons row
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=8, pady=8)

        self.btn_record = tk.Button(
            row, text=t("record", self.cfg.language), font=btn_font,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", bd=0, padx=6, pady=8, command=self._on_record,
        )
        self.btn_stop = tk.Button(
            row, text=t("stop", self.cfg.language), font=btn_font,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", bd=0, padx=6, pady=8, command=self._on_stop,
        )
        self.btn_optimize = tk.Button(
            row, text=t("optimize", self.cfg.language), font=btn_font,
            bg=BTN_BG, fg=FG, activebackground=BTN_ACTIVE, activeforeground=FG,
            relief="flat", bd=0, padx=6, pady=8, command=self._on_optimize,
        )
        for i, b in enumerate((self.btn_record, self.btn_stop, self.btn_optimize)):
            b.grid(row=0, column=i, sticky="ew", padx=3)
            row.columnconfigure(i, weight=1)

        # Status line
        self.status_var = tk.StringVar(value=t("idle", self.cfg.language))
        self.status = tk.Label(
            self.root, textvariable=self.status_var, bg=BG, fg=ACCENT,
            font=status_font, anchor="w",
        )
        self.status.pack(fill="x", padx=11)

        # Text preview
        self.text = tk.Text(
            self.root, height=5, bg="#15161c", fg=FG, insertbackground=FG,
            relief="flat", bd=0, wrap="word", font=("Helvetica", 9),
            padx=8, pady=6,
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    def _wire_controller(self) -> None:
        c = self.controller
        c.on_status = lambda s: self.root.after(0, self._set_status, s)
        c.on_text = lambda s: self.root.after(0, self._set_text, s)
        c.on_state = lambda s: self.root.after(0, self._set_state, s)

    # -- dragging ------------------------------------------------------------
    def _start_drag(self, event) -> None:
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def _on_drag(self, event) -> None:
        x = self.root.winfo_x() + event.x - self._drag["x"]
        y = self.root.winfo_y() + event.y - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    # -- button handlers -----------------------------------------------------
    def _on_record(self) -> None:
        self.controller.start_recording()

    def _on_stop(self) -> None:
        self.controller.stop_recording()

    def _on_optimize(self) -> None:
        self.controller.optimize()

    # -- UI updates (main thread) -------------------------------------------
    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)
        self.status.configure(fg=REC if msg == t("recording", self.cfg.language) else ACCENT)

    def _set_text(self, msg: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", msg)

    def _set_state(self, state: str) -> None:
        """state ∈ {idle, recording, busy} — toggles button availability."""
        if state == "recording":
            self.btn_record.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.btn_optimize.configure(state="disabled")
        elif state == "busy":
            self.btn_record.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.btn_optimize.configure(state="disabled")
        else:  # idle
            self.btn_record.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            has_text = bool(self.controller.draft_text.strip())
            self.btn_optimize.configure(state="normal" if has_text else "disabled")

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    FloatingWindow().run()
