import sys
from pathlib import Path

print("Python executable:", sys.executable)
print("Python version:", sys.version)

sys.path.insert(0, str(Path(__file__).parent.parent))

import flet as ft

from ui.app_controller import AppController


def main(page: ft.Page) -> None:
    AppController(page)

# NOTE: ft.app() is called exclusively from main.py
