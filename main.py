"""
main.py — application entrypoint

TRANSITIONAL: currently launches ui/app.py::main() directly.
Phase 2 will replace this with AppController-driven start.
"""

import flet as ft
from ui.app import main

if __name__ == "__main__":
    ft.app(target=main)
