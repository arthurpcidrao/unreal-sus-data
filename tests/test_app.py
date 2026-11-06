"""Teste automatizado de renderização do Dashboard Streamlit e validação dos filtros e dados enriquecidos."""

from streamlit.testing.v1 import AppTest
from wilson.dashboard import carregar_dados
from wilson.pipeline import BASE_DIR


def main() -> None:
    df_mun, df_mort_hist, df_mort_causas, df_ideb_hist, auditoria = carregar_dados()
    assert len(df_mun) == 184, f"Esperado 184 municípios, obtido {len(df_mun)}"
    assert int(df_mun["TOTAL_ATENDIMENTOS"].sum()) == 204579
    assert int(df_mun["MAIS_ATENDIMENTOS_QUE_HABITANTES"].sum()) == 0
    assert df_mun["CODIGO_IBGE"].isna().sum() == 0

    # 1. Testar estado natural padrão (vazio = todos os 184 municípios)
    at = AppTest.from_file(str(BASE_DIR / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception, f"Exceções no estado padrão: {at.exception}"
    assert at.multiselect(key="filtro_municipios").value == []
    assert at.metric[0].value == "204.579"

    # 2. Testar filtro de um único município (ex: Fortaleza)
    at.multiselect(key="filtro_municipios").select("Fortaleza").run()
    assert not at.exception, f"Exceções ao filtrar Fortaleza: {at.exception}"
    assert at.metric[0].value == "9.364"

    print(
        f"Sucesso! Estado padrão (184 municípios) e filtro individual ('Fortaleza') validados sem erros!"
    )


if __name__ == "__main__":
    main()
