"""Pacote principal do projeto Wilson - Enriquecimento de Dados SUS & IBGE (Ceará)."""

from __future__ import annotations

import json
from wilson.pipeline import executar_enriquecimento


def main() -> None:
    """Executa o pipeline de enriquecimento de dados e exibe o resumo da auditoria."""
    auditoria = executar_enriquecimento()
    print("=== Enriquecimento de Dados SUS & IBGE Concluído ===")
    print(json.dumps(auditoria, ensure_ascii=False, indent=2))
    print("\nPara iniciar o Dashboard BI interativo, execute:")
    print("  uv run streamlit run app.py")
