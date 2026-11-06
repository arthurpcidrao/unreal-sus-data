"""Ponto de entrada principal do Dashboard Streamlit de Inteligência de Dados SUS & IBGE."""

import sys
from pathlib import Path

# Garante que o pacote 'wilson' em src/ seja encontrado mesmo sem instalação editável no Streamlit Cloud
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wilson.dashboard import render_dashboard

if __name__ == "__main__":
    render_dashboard()


