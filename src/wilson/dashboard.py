"""Dashboard interativo em Streamlit para análise dos atendimentos SUS e indicadores IBGE do Ceará."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from wilson.pipeline import BASE_DIR, OUTPUT_DIR, executar_enriquecimento


@st.cache_data(show_spinner="Carregando bases enriquecidas...")
def carregar_dados() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
]:
    """Carrega os datasets enriquecidos do disco (ou executa o pipeline caso ainda não existam)."""
    arq_mun = OUTPUT_DIR / "municipios_enriquecidos.parquet"
    if not arq_mun.exists():
        executar_enriquecimento()

    df_mun = pd.read_parquet(arq_mun)
    df_mort_hist = pd.read_csv(OUTPUT_DIR / "mortalidade_historico.csv")
    df_mort_causas = pd.read_csv(OUTPUT_DIR / "mortalidade_causas_2022.csv")
    df_ideb_hist = pd.read_csv(OUTPUT_DIR / "ideb_historico.csv")
    with open(OUTPUT_DIR / "relatorio_auditoria.json", mode="r", encoding="utf-8") as f:
        auditoria = json.load(f)

    bins = [0, 20_000, 50_000, 100_000, 10_000_000]
    labels = [
        "1. Pequeno Porte (< 20 mil)",
        "2. Médio Porte (20 a 50 mil)",
        "3. Médio-Grande (50 a 100 mil)",
        "4. Grande Porte (> 100 mil)",
    ]
    df_mun["PORTE_POPULACIONAL"] = pd.cut(
        df_mun["POPULACAO_2022"], bins=bins, labels=labels
    ).astype(str)

    return df_mun, df_mort_hist, df_mort_causas, df_ideb_hist, auditoria


@st.cache_data(show_spinner="Carregando amostra da base individual de atendimentos...")
def carregar_amostra_atendimentos(
    chaves_municipios: tuple[str, ...] | None = None, limite: int = 1000
) -> pd.DataFrame:
    """Carrega registros individuais enriquecidos da tabela de 204.579 atendimentos."""
    arq_atend = OUTPUT_DIR / "atendimentos_enriquecidos.parquet"
    df_atend = pd.read_parquet(arq_atend)
    if chaves_municipios:
        df_atend = df_atend[df_atend["MUNICIPIO_CHAVE"].isin(chaves_municipios)]
    return df_atend.head(limite)


def formatar_int(valor: float | int) -> str:
    """Formata inteiro com separador de milhar no padrão brasileiro."""
    return f"{int(round(valor)):,}".replace(",", ".")


def formatar_dec(valor: float, casas: int = 2) -> str:
    """Formata número decimal no padrão brasileiro."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def limpar_filtros() -> None:
    """Reseta os filtros da barra lateral para o estado natural (todos os 184 municípios)."""
    st.session_state["filtro_municipios"] = []
    st.session_state["filtro_regioes"] = []
    st.session_state["filtro_portes"] = []


def render_dashboard() -> None:
    """Renderiza a aplicação completa do Streamlit."""
    st.set_page_config(
        page_title="BI Atendimentos SUS & Indicadores IBGE - Ceará",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    df_mun, df_mort_hist, df_mort_causas, df_ideb_hist, auditoria = carregar_dados()

    # Médias de referência estadual (184 municípios) para comparação imediata
    media_ce_100k = float(df_mun["ATENDIMENTOS_POR_100K_HAB"].mean())
    taxa_global_ce_100k = float(
        df_mun["TOTAL_ATENDIMENTOS"].sum() / df_mun["POPULACAO_2022"].sum() * 100_000
    )
    media_ce_idh = float(df_mun["IDH_2010"].mean())
    media_ce_pobreza = float(df_mun["INCIDENCIA_POBREZA_PCT"].mean())
    media_ce_mortalidade = float(df_mun["TAXA_MORTALIDADE_1000_HAB"].mean())

    # -------------------------------------------------------------------------
    # SIDEBAR - ESTADO NATURAL = TODOS OS MUNICÍPIOS (SEM TAGS PRÉ-PREENCHIDAS)
    # -------------------------------------------------------------------------
    with st.sidebar:
        svg_path = BASE_DIR / "SUS_apenas_preenchimento.svg"
        if svg_path.exists():
            st.image(str(svg_path), width=170)

        st.markdown("## 🔎 Filtros de Apresentação")
        st.caption(
            "Por padrão (**vazio**), o painel apresenta **todos os 184 municípios do Ceará**. "
            "Selecione um município ou região abaixo apenas quando quiser isolar o recorte."
        )

        todas_opcoes_mun = sorted(df_mun["MUNICIPIO"].unique().tolist())
        municipios_busca = st.multiselect(
            "Apresentar Município(s):",
            options=todas_opcoes_mun,
            default=[],
            key="filtro_municipios",
            placeholder="Todos os 184 municípios (digite para filtrar)",
        )

        tipo_regiao_label = st.radio(
            "Agrupamento Regional:",
            options=["Macrorregião de Saúde (SUS)", "Mesorregião (IBGE)"],
            index=0,
            help="Define a divisão regional exibida nos gráficos e tabelas.",
        )
        col_regiao = (
            "MACRORREGIAO_SAUDE"
            if tipo_regiao_label == "Macrorregião de Saúde (SUS)"
            else "MESORREGIAO"
        )

        regioes_disponiveis = sorted(df_mun[col_regiao].dropna().unique().tolist())
        regioes_selecionadas = st.multiselect(
            f"Filtrar {tipo_regiao_label} (Opcional):",
            options=regioes_disponiveis,
            default=[],
            key="filtro_regioes",
            placeholder="Todas as regiões",
        )

        portes_disponiveis = sorted(df_mun["PORTE_POPULACIONAL"].unique().tolist())
        portes_selecionados = st.multiselect(
            "Filtrar Porte Populacional (Opcional):",
            options=portes_disponiveis,
            default=[],
            key="filtro_portes",
            placeholder="Todos os portes populacionais",
        )

        top_n = st.slider(
            "Municípios nos Rankings (Top / Bottom N):",
            min_value=5,
            max_value=30,
            value=15,
            step=5,
        )

        tem_filtro_ativo = bool(
            municipios_busca or regioes_selecionadas or portes_selecionados
        )
        if tem_filtro_ativo:
            st.button(
                "🔄 Mostrar Todos os 184 Municípios",
                on_click=limpar_filtros,
                width="stretch",
            )

        st.divider()
        st.info(
            "**Regra de Contagem:** Cada `ID` representa **1 atendimento único** "
            "(204.579 no total). Primeiros nomes repetidos **não** são contados como a mesma pessoa."
        )

    # Aplicação natural dos filtros (vazio = entra tudo)
    df_filtrado = df_mun.copy()
    if regioes_selecionadas:
        df_filtrado = df_filtrado[df_filtrado[col_regiao].isin(regioes_selecionadas)]
    if portes_selecionados:
        df_filtrado = df_filtrado[
            df_filtrado["PORTE_POPULACIONAL"].isin(portes_selecionados)
        ]
    if municipios_busca:
        df_filtrado = df_filtrado[df_filtrado["MUNICIPIO"].isin(municipios_busca)]

    if df_filtrado.empty:
        st.warning(
            "Nenhum município corresponde à combinação de filtros. Clique em 'Mostrar Todos os 184 Municípios' na barra lateral."
        )
        return

    # -------------------------------------------------------------------------
    # CABEÇALHO E KPIS GLOBAIS
    # -------------------------------------------------------------------------
    st.title("Inteligência de Dados SUS & Enriquecimento Demográfico (IBGE)")
    if municipios_busca:
        st.caption(
            f"🎯 **Modo de Apresentação Focado:** Exibindo dados exclusivos de **{', '.join(municipios_busca)}** "
            "comparados às médias estaduais do Ceará (184 municípios)."
        )
    else:
        st.caption(
            "Visão integral dos **184 municípios do Ceará**: base de Atendimentos SUS (`DADOS.txt`) "
            "enriquecida com Censo Demográfico 2022, Mortalidade (2006–2022), Mapa de Pobreza e Desigualdade (Gini), "
            "IDH Municipal e IDEB (2005–2025)."
        )

    total_atend = int(df_filtrado["TOTAL_ATENDIMENTOS"].sum())
    total_pop = int(df_filtrado["POPULACAO_2022"].sum())
    taxa_recorte_100k = (total_atend / total_pop * 100_000) if total_pop > 0 else 0.0
    media_mun_100k = float(df_filtrado["ATENDIMENTOS_POR_100K_HAB"].mean())
    qtd_mun_excesso = int(df_filtrado["MAIS_ATENDIMENTOS_QUE_HABITANTES"].sum())
    media_pobreza = float(df_filtrado["INCIDENCIA_POBREZA_PCT"].mean())
    media_idh = float(df_filtrado["IDH_2010"].mean())
    total_obitos_2022 = int(df_filtrado["OBITOS_2022"].sum())
    taxa_mort_recorte = (total_obitos_2022 / total_pop * 1000) if total_pop > 0 else 0.0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
        "Total de Atendimentos (IDs)",
        formatar_int(total_atend),
        f"{len(df_filtrado)} de 184 municípios",
    )
    k2.metric(
        "População Residente (2022)",
        formatar_int(total_pop),
        f"{formatar_dec(total_pop / df_mun['POPULACAO_2022'].sum() * 100, 1)}% da pop. do CE",
    )
    k3.metric(
        "Atendimentos / 100 mil hab",
        formatar_dec(taxa_recorte_100k, 1),
        f"Média mun.: {formatar_dec(media_mun_100k, 1)} (CE: {formatar_dec(media_ce_100k, 0)})",
    )
    k4.metric(
        "IDH Municipal Médio (2010)",
        formatar_dec(media_idh, 3),
        f"Média CE: {formatar_dec(media_ce_idh, 3)}",
    )
    k5.metric(
        "Incidência Média de Pobreza",
        f"{formatar_dec(media_pobreza, 1)}%",
        f"Média CE: {formatar_dec(media_ce_pobreza, 1)}%",
    )
    k6.metric(
        "Óbitos (2022) & Taxa / 1k hab",
        formatar_int(total_obitos_2022),
        f"{formatar_dec(taxa_mort_recorte, 2)}/1k (CE: {formatar_dec(media_ce_mortalidade, 2)})",
    )

    # Se o usuário filtrou 1 ou poucos municípios, mostrar Ficha Comparativa Direta
    if 1 <= len(df_filtrado) <= 5:
        with st.container(border=True):
            st.markdown(
                "#### 📌 Comparativo Direto: Município(s) Selecionado(s) vs. Média dos Municípios do Ceará"
            )
            cols_comp = [
                "MUNICIPIO",
                "CODIGO_IBGE",
                col_regiao,
                "TOTAL_ATENDIMENTOS",
                "POPULACAO_2022",
                "ATENDIMENTOS_POR_100K_HAB",
                "RANK_PROPORCIONAL_100K",
                "IDH_2010",
                "INCIDENCIA_POBREZA_PCT",
                "INDICE_GINI",
                "OBITOS_2022",
                "TAXA_MORTALIDADE_1000_HAB",
                "IDEB_AI_2023",
            ]
            df_comp = df_filtrado[cols_comp].copy()
            linha_media_ce = pd.DataFrame(
                [
                    {
                        "MUNICIPIO": "📊 MÉDIA MUNICIPAL DO CEARÁ (184 mun.)",
                        "CODIGO_IBGE": 2300000,
                        col_regiao: "Ceará (Referência)",
                        "TOTAL_ATENDIMENTOS": int(df_mun["TOTAL_ATENDIMENTOS"].mean()),
                        "POPULACAO_2022": int(df_mun["POPULACAO_2022"].mean()),
                        "ATENDIMENTOS_POR_100K_HAB": round(media_ce_100k, 2),
                        "RANK_PROPORCIONAL_100K": 92,
                        "IDH_2010": round(media_ce_idh, 3),
                        "INCIDENCIA_POBREZA_PCT": round(media_ce_pobreza, 2),
                        "INDICE_GINI": round(float(df_mun["INDICE_GINI"].mean()), 2),
                        "OBITOS_2022": int(df_mun["OBITOS_2022"].mean()),
                        "TAXA_MORTALIDADE_1000_HAB": round(media_ce_mortalidade, 2),
                        "IDEB_AI_2023": round(float(df_mun["IDEB_AI_2023"].mean()), 2),
                    }
                ]
            )
            st.dataframe(
                pd.concat([df_comp, linha_media_ce], ignore_index=True),
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # -------------------------------------------------------------------------
    # NAVEGAÇÃO EM ABAS
    # -------------------------------------------------------------------------
    aba_mapa, aba_ranking, aba_socio, aba_coerencia = st.tabs(
        [
            "🗺️ Mapa Interativo & Volume Regional",
            "🏆 Proporção (100k hab) & Rankings",
            "🏥 Mortalidade, Pobreza, IDH & Correlações",
            "✅ Coerência, Auditoria & Dados Enriquecidos",
        ]
    )

    # =========================================================================
    # ABA 1: MAPA INTERATIVO & VOLUME POR REGIÃO E MUNICÍPIO
    # =========================================================================
    with aba_mapa:
        st.subheader("🗺️ Mapa Interativo dos Atendimentos SUS no Ceará")
        st.markdown(
            "As **bolas possuem tamanhos proporcionais à densidade/volume de atendimentos** "
            "(contabilizados pelo `ID` único de cada atendimento). Use os controles abaixo para "
            "alternar o tamanho e a cor das bolhas."
        )

        opcoes_tamanho = {
            "Volume Absoluto de Atendimentos (IDs Únicos)": "TOTAL_ATENDIMENTOS",
            "Proporção de Atendimentos por 100 mil Habitantes": "ATENDIMENTOS_POR_100K_HAB",
            "Densidade Territorial (Atendimentos por km²)": "ATENDIMENTOS_POR_KM2",
        }
        opcoes_cor = {
            "Proporção de Atendimentos por 100 mil Habitantes": "ATENDIMENTOS_POR_100K_HAB",
            "Volume Absoluto de Atendimentos (IDs Únicos)": "TOTAL_ATENDIMENTOS",
            tipo_regiao_label: col_regiao,
            "IDH Municipal (2010)": "IDH_2010",
            "Incidência da Pobreza (%)": "INCIDENCIA_POBREZA_PCT",
            "Índice de Gini (Desigualdade)": "INDICE_GINI",
            "Taxa de Mortalidade por 1.000 hab (2022)": "TAXA_MORTALIDADE_1000_HAB",
            "IDEB Anos Iniciais - Rede Pública (2023)": "IDEB_AI_2023",
            "Cobertura de Água - Rede Geral (%)": "PCT_AGUA_REDE_GERAL",
        }

        cm1, cm2, cm3, cm4 = st.columns([2, 2, 1, 1])
        with cm1:
            label_tam = st.selectbox(
                "Tamanho da Bola (Densidade):",
                options=list(opcoes_tamanho.keys()),
                index=0,
            )
        with cm2:
            label_cor = st.selectbox(
                "Cor da Bola (Indicador):",
                options=list(opcoes_cor.keys()),
                index=0,
            )
        with cm3:
            raio_max = st.slider(
                "Raio Máximo da Bola:", min_value=20, max_value=65, value=42
            )
        with cm4:
            estilo_mapa = st.selectbox(
                "Estilo do Mapa:",
                options=["carto-positron", "open-street-map", "carto-darkmatter"],
                index=0,
            )

        col_tam_mapa = opcoes_tamanho[label_tam]
        col_cor_mapa = opcoes_cor[label_cor]

        # Se apenas 1 ou poucos municípios estiverem filtrados, centralizar o mapa neles
        lat_centro = (
            float(df_filtrado["LATITUDE"].mean())
            if len(df_filtrado) <= 10
            else -5.20
        )
        lon_centro = (
            float(df_filtrado["LONGITUDE"].mean())
            if len(df_filtrado) <= 10
            else -39.50
        )
        zoom_mapa = 8.5 if len(df_filtrado) == 1 else (7.2 if len(df_filtrado) <= 10 else 6.3)

        fig_mapa = px.scatter_map(
            df_filtrado,
            lat="LATITUDE",
            lon="LONGITUDE",
            size=col_tam_mapa,
            color=col_cor_mapa,
            hover_name="MUNICIPIO",
            hover_data={
                "CODIGO_IBGE": True,
                col_regiao: True,
                "TOTAL_ATENDIMENTOS": ":,",
                "POPULACAO_2022": ":,",
                "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                "PROPORCAO_POP_ATENDIDA_PCT": ":.2f",
                "IDH_2010": ":.3f",
                "INCIDENCIA_POBREZA_PCT": ":.2f",
                "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                "IDEB_AI_2023": ":.1f",
                "LATITUDE": False,
                "LONGITUDE": False,
            },
            labels={
                "CODIGO_IBGE": "Código IBGE",
                col_regiao: tipo_regiao_label,
                "TOTAL_ATENDIMENTOS": "Atendimentos (IDs)",
                "POPULACAO_2022": "População (2022)",
                "ATENDIMENTOS_POR_100K_HAB": "Atend. / 100k hab",
                "PROPORCAO_POP_ATENDIDA_PCT": "% Pop. Atendida",
                "ATENDIMENTOS_POR_KM2": "Atend. / km²",
                "INCIDENCIA_POBREZA_PCT": "Pobreza (%)",
                "INDICE_GINI": "Índice de Gini",
                "TAXA_MORTALIDADE_1000_HAB": "Mortalidade / 1k hab",
                "IDH_2010": "IDH (2010)",
                "IDEB_AI_2023": "IDEB Anos Iniciais (2023)",
                "PCT_AGUA_REDE_GERAL": "Água Rede Geral (%)",
            },
            color_continuous_scale="Viridis" if col_cor_mapa != col_regiao else None,
            size_max=raio_max,
            zoom=zoom_mapa,
            center={"lat": lat_centro, "lon": lon_centro},
            map_style=estilo_mapa,
            height=620,
            title=f"Mapa de Densidade dos Atendimentos SUS — Tamanho: {label_tam} | Cor: {label_cor}",
        )
        fig_mapa.update_layout(margin={"r": 10, "t": 45, "l": 10, "b": 10})
        st.plotly_chart(fig_mapa, width="stretch")

        st.divider()
        st.subheader(f"📊 Volume de Atendimentos por {tipo_regiao_label} e Município")

        df_reg = (
            df_filtrado.groupby(col_regiao, as_index=False)
            .agg(
                TOTAL_ATENDIMENTOS=("TOTAL_ATENDIMENTOS", "sum"),
                POPULACAO_2022=("POPULACAO_2022", "sum"),
                QTD_MUNICIPIOS=("MUNICIPIO", "count"),
                OBITOS_2022=("OBITOS_2022", "sum"),
                POBREZA_MEDIA=("INCIDENCIA_POBREZA_PCT", "mean"),
                IDH_MEDIO=("IDH_2010", "mean"),
            )
            .sort_values("TOTAL_ATENDIMENTOS", ascending=True)
        )
        df_reg["ATENDIMENTOS_POR_100K_HAB"] = (
            df_reg["TOTAL_ATENDIMENTOS"] / df_reg["POPULACAO_2022"] * 100_000
        ).round(2)
        df_reg["PARTICIPACAO_ATEND_PCT"] = (
            df_reg["TOTAL_ATENDIMENTOS"] / df_reg["TOTAL_ATENDIMENTOS"].sum() * 100
        ).round(2)

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            fig_reg_vol = px.bar(
                df_reg,
                x="TOTAL_ATENDIMENTOS",
                y=col_regiao,
                orientation="h",
                text="TOTAL_ATENDIMENTOS",
                color="ATENDIMENTOS_POR_100K_HAB",
                color_continuous_scale="Blues",
                hover_data={
                    "POPULACAO_2022": ":,",
                    "QTD_MUNICIPIOS": True,
                    "PARTICIPACAO_ATEND_PCT": ":.2f",
                    "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                    "IDH_MEDIO": ":.3f",
                },
                labels={
                    col_regiao: tipo_regiao_label,
                    "TOTAL_ATENDIMENTOS": "Volume de Atendimentos (IDs)",
                    "ATENDIMENTOS_POR_100K_HAB": "Atend. / 100k hab",
                    "POPULACAO_2022": "População 2022",
                    "QTD_MUNICIPIOS": "Nº de Municípios",
                    "PARTICIPACAO_ATEND_PCT": "% do Total de Atendimentos",
                    "IDH_MEDIO": "IDH Médio",
                },
                title=f"Volume Total de Atendimentos por {tipo_regiao_label}",
                height=440,
            )
            fig_reg_vol.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig_reg_vol.update_layout(yaxis_title=None)
            st.plotly_chart(fig_reg_vol, width="stretch")

        with col_r2:
            df_reg_prop = df_reg.sort_values(
                "ATENDIMENTOS_POR_100K_HAB", ascending=True
            )
            fig_reg_prop = px.bar(
                df_reg_prop,
                x="ATENDIMENTOS_POR_100K_HAB",
                y=col_regiao,
                orientation="h",
                text="ATENDIMENTOS_POR_100K_HAB",
                color="POBREZA_MEDIA",
                color_continuous_scale="YlOrRd",
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "POPULACAO_2022": ":,",
                    "POBREZA_MEDIA": ":.2f",
                    "IDH_MEDIO": ":.3f",
                },
                labels={
                    col_regiao: tipo_regiao_label,
                    "ATENDIMENTOS_POR_100K_HAB": "Atendimentos por 100 mil hab.",
                    "POBREZA_MEDIA": "Pobreza Média (%)",
                    "IDH_MEDIO": "IDH Médio",
                },
                title=f"Proporção Regional por 100 mil hab. vs. Pobreza Média",
                height=440,
            )
            fig_reg_prop.add_vline(
                x=taxa_global_ce_100k,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Taxa Global CE ({formatar_dec(taxa_global_ce_100k, 0)})",
            )
            fig_reg_prop.update_traces(
                texttemplate="%{text:,.1f}", textposition="outside"
            )
            fig_reg_prop.update_layout(yaxis_title=None)
            st.plotly_chart(fig_reg_prop, width="stretch")

        fig_treemap = px.treemap(
            df_filtrado,
            path=[px.Constant("Ceará"), col_regiao, "MUNICIPIO"],
            values="TOTAL_ATENDIMENTOS",
            color="ATENDIMENTOS_POR_100K_HAB",
            color_continuous_scale="Tealgrn",
            hover_data={
                "POPULACAO_2022": ":,",
                "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                "IDH_2010": ":.3f",
                "INCIDENCIA_POBREZA_PCT": ":.2f",
                "TAXA_MORTALIDADE_1000_HAB": ":.2f",
            },
            labels={
                "TOTAL_ATENDIMENTOS": "Volume de Atendimentos",
                "ATENDIMENTOS_POR_100K_HAB": "Atend. / 100k hab",
                "POPULACAO_2022": "População 2022",
                "IDH_2010": "IDH (2010)",
                "INCIDENCIA_POBREZA_PCT": "Pobreza (%)",
                "TAXA_MORTALIDADE_1000_HAB": "Mortalidade / 1k hab",
            },
            title=(
                f"Mapa de Árvore (Treemap): Hierarquia {tipo_regiao_label} ➔ Município "
                "(Área = Volume de Atendimentos | Cor = Proporção por 100k hab)"
            ),
            height=540,
        )
        st.plotly_chart(fig_treemap, width="stretch")

    # =========================================================================
    # ABA 2: PROPORÇÃO POR 100 MIL HABITANTES & RANKINGS MUNICIPAIS
    # =========================================================================
    with aba_ranking:
        st.subheader(
            f"🏆 Ranking de Municípios: Maior e Menor Volume Proporcional de Atendimento (Top {top_n})"
        )
        st.markdown(
            f"Comparação direta com a **média municipal do Ceará ({formatar_dec(media_ce_100k, 2)} atend./100k hab)** "
            f"e a **taxa ponderada estadual ({formatar_dec(taxa_global_ce_100k, 2)} atend./100k hab)**."
        )

        df_top_prop = (
            df_filtrado.sort_values("ATENDIMENTOS_POR_100K_HAB", ascending=False)
            .head(top_n)
            .sort_values("ATENDIMENTOS_POR_100K_HAB", ascending=True)
        )
        df_bot_prop = (
            df_filtrado.sort_values("ATENDIMENTOS_POR_100K_HAB", ascending=True)
            .head(top_n)
            .sort_values("ATENDIMENTOS_POR_100K_HAB", ascending=False)
        )

        rk1, rk2 = st.columns(2)
        with rk1:
            fig_top_prop = px.bar(
                df_top_prop,
                x="ATENDIMENTOS_POR_100K_HAB",
                y="MUNICIPIO",
                orientation="h",
                color=col_regiao,
                text="ATENDIMENTOS_POR_100K_HAB",
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "POPULACAO_2022": ":,",
                    "PROPORCAO_POP_ATENDIDA_PCT": ":.2f",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                },
                labels={
                    "MUNICIPIO": "Município",
                    "ATENDIMENTOS_POR_100K_HAB": "Atendimentos / 100 mil hab.",
                    col_regiao: tipo_regiao_label,
                    "TOTAL_ATENDIMENTOS": "Atendimentos (IDs)",
                    "POPULACAO_2022": "População 2022",
                    "PROPORCAO_POP_ATENDIDA_PCT": "% Pop. Atendida",
                    "IDH_2010": "IDH (2010)",
                    "INCIDENCIA_POBREZA_PCT": "Pobreza (%)",
                    "TAXA_MORTALIDADE_1000_HAB": "Mortalidade / 1k hab",
                },
                title=f"🔼 Top {top_n} MAIOR Proporção (Atendimentos / 100 mil hab)",
                height=max(420, top_n * 28),
            )
            fig_top_prop.update_traces(
                texttemplate="%{text:,.1f}", textposition="outside"
            )
            fig_top_prop.update_layout(yaxis_title=None, showlegend=True)
            st.plotly_chart(fig_top_prop, width="stretch")

        with rk2:
            fig_bot_prop = px.bar(
                df_bot_prop,
                x="ATENDIMENTOS_POR_100K_HAB",
                y="MUNICIPIO",
                orientation="h",
                color=col_regiao,
                text="ATENDIMENTOS_POR_100K_HAB",
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "POPULACAO_2022": ":,",
                    "PROPORCAO_POP_ATENDIDA_PCT": ":.2f",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                },
                labels={
                    "MUNICIPIO": "Município",
                    "ATENDIMENTOS_POR_100K_HAB": "Atendimentos / 100 mil hab.",
                    col_regiao: tipo_regiao_label,
                    "TOTAL_ATENDIMENTOS": "Atendimentos (IDs)",
                    "POPULACAO_2022": "População 2022",
                    "PROPORCAO_POP_ATENDIDA_PCT": "% Pop. Atendida",
                    "IDH_2010": "IDH (2010)",
                    "INCIDENCIA_POBREZA_PCT": "Pobreza (%)",
                    "TAXA_MORTALIDADE_1000_HAB": "Mortalidade / 1k hab",
                },
                title=f"🔽 Top {top_n} MENOR Proporção (Atendimentos / 100 mil hab)",
                height=max(420, top_n * 28),
            )
            fig_bot_prop.update_traces(
                texttemplate="%{text:,.1f}", textposition="outside"
            )
            fig_bot_prop.update_layout(yaxis_title=None, showlegend=True)
            st.plotly_chart(fig_bot_prop, width="stretch")

        st.divider()
        st.subheader(
            f"📈 Ranking por Volume Absoluto de Atendimentos (Top {top_n} Maiores vs. Menores)"
        )

        df_top_abs = (
            df_filtrado.sort_values("TOTAL_ATENDIMENTOS", ascending=False)
            .head(top_n)
            .sort_values("TOTAL_ATENDIMENTOS", ascending=True)
        )
        df_bot_abs = (
            df_filtrado.sort_values("TOTAL_ATENDIMENTOS", ascending=True)
            .head(top_n)
            .sort_values("TOTAL_ATENDIMENTOS", ascending=False)
        )

        ab1, ab2 = st.columns(2)
        with ab1:
            fig_top_abs = px.bar(
                df_top_abs,
                x="TOTAL_ATENDIMENTOS",
                y="MUNICIPIO",
                orientation="h",
                color="IDH_2010",
                color_continuous_scale="Viridis",
                text="TOTAL_ATENDIMENTOS",
                hover_data={
                    "POPULACAO_2022": ":,",
                    "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                    col_regiao: True,
                },
                labels={
                    "TOTAL_ATENDIMENTOS": "Total de Atendimentos (IDs)",
                    "IDH_2010": "IDH (2010)",
                },
                title=f"🔼 Top {top_n} Maior Volume Absoluto de Atendimentos (Cor = IDH)",
                height=max(400, top_n * 26),
            )
            fig_top_abs.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig_top_abs.update_layout(yaxis_title=None)
            st.plotly_chart(fig_top_abs, width="stretch")

        with ab2:
            fig_bot_abs = px.bar(
                df_bot_abs,
                x="TOTAL_ATENDIMENTOS",
                y="MUNICIPIO",
                orientation="h",
                color="IDH_2010",
                color_continuous_scale="Viridis",
                text="TOTAL_ATENDIMENTOS",
                hover_data={
                    "POPULACAO_2022": ":,",
                    "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                    col_regiao: True,
                },
                labels={
                    "TOTAL_ATENDIMENTOS": "Total de Atendimentos (IDs)",
                    "IDH_2010": "IDH (2010)",
                },
                title=f"🔽 Top {top_n} Menor Volume Absoluto de Atendimentos (Cor = IDH)",
                height=max(400, top_n * 26),
            )
            fig_bot_abs.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig_bot_abs.update_layout(yaxis_title=None)
            st.plotly_chart(fig_bot_abs, width="stretch")

        st.divider()
        st.subheader("📐 Distribuição da Proporção de Atendimentos por 100 mil Habitantes")

        dist1, dist2 = st.columns(2)
        with dist1:
            fig_box = px.box(
                df_filtrado,
                x=col_regiao,
                y="ATENDIMENTOS_POR_100K_HAB",
                color=col_regiao,
                points="all",
                hover_name="MUNICIPIO",
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "POPULACAO_2022": ":,",
                    "IDH_2010": ":.3f",
                },
                labels={
                    col_regiao: tipo_regiao_label,
                    "ATENDIMENTOS_POR_100K_HAB": "Atendimentos por 100 mil hab.",
                },
                title=f"Dispersão Municipal (Boxplot) da Taxa por 100 mil hab. por {tipo_regiao_label}",
                height=460,
            )
            fig_box.update_layout(showlegend=False)
            st.plotly_chart(fig_box, width="stretch")

        with dist2:
            fig_pop_prop = px.scatter(
                df_filtrado,
                x="POPULACAO_2022",
                y="ATENDIMENTOS_POR_100K_HAB",
                size="TOTAL_ATENDIMENTOS",
                color="PORTE_POPULACIONAL",
                hover_name="MUNICIPIO",
                log_x=True,
                size_max=40,
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    col_regiao: True,
                },
                labels={
                    "POPULACAO_2022": "População Residente 2022 (Escala Log)",
                    "ATENDIMENTOS_POR_100K_HAB": "Atendimentos por 100 mil hab.",
                    "PORTE_POPULACIONAL": "Porte Populacional",
                },
                title="Relação Porte Populacional (Log) vs. Cobertura por 100 mil Habitantes",
                height=460,
            )
            st.plotly_chart(fig_pop_prop, width="stretch")

    # =========================================================================
    # ABA 3: MORTALIDADE, POBREZA, DESIGUALDADE, IDH & EDUCAÇÃO (IDEB)
    # =========================================================================
    with aba_socio:
        st.subheader(
            "🔬 Cruzamento Direto: Atendimentos vs. Mortalidade, IDH e Pobreza"
        )
        st.markdown(
            "Análise de correlação para responder: **Onde há mais atendimentos ocorrem mais mortes? "
            "Como os atendimentos se comportam frente ao IDH e à Pobreza?**\n"
            "- **Atendimentos/100k hab vs. Taxa de Mortalidade/1k hab:** Correlação nula ($r = +0,0015$) — maior cobertura de atendimentos SUS **não** está associada a maior mortalidade.\n"
            "- **Atendimentos/100k hab vs. IDH (2010):** Correlação negativa moderada ($r = -0,3920$) — municípios com menor IDH dependem mais intensamente do SUS.\n"
            "- **Atendimentos/100k hab vs. Incidência de Pobreza (%):** Correlação positiva ($r = +0,2301$) — maior vulnerabilidade social gera maior demanda proporcional pelo SUS."
        )

        opcoes_x_socio = {
            "IDH Municipal (2010)": "IDH_2010",
            "Incidência da Pobreza (%)": "INCIDENCIA_POBREZA_PCT",
            "Taxa Bruta de Mortalidade por 1.000 hab (2022)": "TAXA_MORTALIDADE_1000_HAB",
            "Óbitos Totais em 2022 (Absoluto)": "OBITOS_2022",
            "Incidência da Pobreza Subjetiva (%)": "INCIDENCIA_POBREZA_SUBJETIVA_PCT",
            "Índice de Gini (Desigualdade de Renda)": "INDICE_GINI",
            "IDEB Anos Iniciais - Rede Pública (2023)": "IDEB_AI_2023",
            "IDEB Anos Finais - Rede Pública (2023)": "IDEB_AF_2023",
            "Domicílios com Água da Rede Geral (%)": "PCT_AGUA_REDE_GERAL",
            "Domicílios com Esgoto ou Fossa Ligada à Rede (%)": "PCT_ESGOTO_REDE_OU_FOSSA",
            "Domicílios com Coleta de Lixo (%)": "PCT_LIXO_COLETADO",
            "Índice de Envelhecimento (60+ / 0-14 anos)": "INDICE_ENVELHECIMENTO",
        }
        opcoes_y_socio = {
            "Proporção de Atendimentos por 100 mil Habitantes": "ATENDIMENTOS_POR_100K_HAB",
            "Volume Absoluto de Atendimentos (IDs)": "TOTAL_ATENDIMENTOS",
            "Taxa Bruta de Mortalidade por 1.000 hab (2022)": "TAXA_MORTALIDADE_1000_HAB",
            "Incidência da Pobreza (%)": "INCIDENCIA_POBREZA_PCT",
        }

        sc1, sc2 = st.columns(2)
        with sc1:
            eixo_x_label = st.selectbox(
                "Indicador Socioeconômico / Epidemiológico (Eixo X):",
                options=list(opcoes_x_socio.keys()),
                index=0,
            )
        with sc2:
            eixo_y_label = st.selectbox(
                "Métrica de Saúde / Atendimentos (Eixo Y):",
                options=list(opcoes_y_socio.keys()),
                index=0,
            )

        col_x = opcoes_x_socio[eixo_x_label]
        col_y = opcoes_y_socio[eixo_y_label]

        df_corr_plot = df_filtrado.dropna(subset=[col_x, col_y]).copy()
        r_pearson = (
            float(df_corr_plot[col_x].corr(df_corr_plot[col_y]))
            if len(df_corr_plot) > 2
            else 0.0
        )

        col_sc_plot, col_heat = st.columns([3, 2])
        with col_sc_plot:
            fig_sc = px.scatter(
                df_corr_plot,
                x=col_x,
                y=col_y,
                size="POPULACAO_2022",
                color=col_regiao,
                hover_name="MUNICIPIO",
                size_max=38,
                hover_data={
                    "TOTAL_ATENDIMENTOS": ":,",
                    "ATENDIMENTOS_POR_100K_HAB": ":,.2f",
                    "IDH_2010": ":.3f",
                    "INCIDENCIA_POBREZA_PCT": ":.2f",
                    "TAXA_MORTALIDADE_1000_HAB": ":.2f",
                },
                labels={
                    col_x: eixo_x_label,
                    col_y: eixo_y_label,
                    col_regiao: tipo_regiao_label,
                },
                title=f"{eixo_x_label} vs. {eixo_y_label} (Correlação r = {r_pearson:.2f})",
                height=460,
            )
            if len(df_corr_plot) > 2:
                x_vals = df_corr_plot[col_x].to_numpy(dtype=float)
                y_vals = df_corr_plot[col_y].to_numpy(dtype=float)
                coef = np.polyfit(x_vals, y_vals, 1)
                x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
                y_line = coef[0] * x_line + coef[1]
                fig_sc.add_trace(
                    go.Scatter(
                        x=x_line,
                        y=y_line,
                        mode="lines",
                        name="Tendência Linear",
                        line={"color": "#e11d48", "dash": "dash", "width": 2},
                    )
                )
            st.plotly_chart(fig_sc, width="stretch")

        with col_heat:
            cols_matriz = [
                "ATENDIMENTOS_POR_100K_HAB",
                "TOTAL_ATENDIMENTOS",
                "IDH_2010",
                "INCIDENCIA_POBREZA_PCT",
                "INDICE_GINI",
                "TAXA_MORTALIDADE_1000_HAB",
                "OBITOS_2022",
                "IDEB_AI_2023",
                "PCT_AGUA_REDE_GERAL",
            ]
            nomes_curtos = [
                "Atend./100k",
                "Atend. Abs.",
                "IDH (2010)",
                "Pobreza (%)",
                "Gini",
                "Mort./1k hab",
                "Óbitos Abs.",
                "IDEB AI 23",
                "Água Rede %",
            ]
            corr_mat = df_filtrado[cols_matriz].corr().round(2)
            corr_mat.index = nomes_curtos
            corr_mat.columns = nomes_curtos

            fig_heat = px.imshow(
                corr_mat,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                zmin=-1,
                zmax=1,
                aspect="auto",
                title="Matriz de Correlação Multivariada (Pearson)",
                height=460,
            )
            st.plotly_chart(fig_heat, width="stretch")

        st.divider()
        st.subheader(
            "🩺 Análise Epidemiológica de Mortalidade (2006–2022 e Capítulos CID-10)"
        )

        chaves_filtradas = set(df_filtrado["MUNICIPIO_CHAVE"].unique())
        df_mh_f = df_mort_hist[
            df_mort_hist["MUNICIPIO_CHAVE"].isin(chaves_filtradas)
        ]
        df_mc_f = df_mort_causas[
            df_mort_causas["MUNICIPIO_CHAVE"].isin(chaves_filtradas)
        ]

        m1, m2 = st.columns(2)
        with m1:
            df_mh_serie = (
                df_mh_f.groupby(["ANO", col_regiao], as_index=False)["OBITOS"].sum()
            )
            fig_mort_tempo = px.line(
                df_mh_serie,
                x="ANO",
                y="OBITOS",
                color=col_regiao,
                markers=True,
                labels={
                    "ANO": "Ano do Óbito",
                    "OBITOS": "Total de Óbitos Registrados",
                    col_regiao: tipo_regiao_label,
                },
                title=f"Evolução Histórica de Óbitos por {tipo_regiao_label} (2006–2022)",
                height=430,
            )
            fig_mort_tempo.add_vrect(
                x0=2019.8,
                x1=2021.5,
                fillcolor="red",
                opacity=0.10,
                line_width=0,
                annotation_text="Pico Pandemia COVID-19",
                annotation_position="top left",
            )
            st.plotly_chart(fig_mort_tempo, width="stretch")

        with m2:
            df_causas_agg = (
                df_mc_f.groupby("CAUSA_CID10", as_index=False)["OBITOS_2022"]
                .sum()
                .sort_values("OBITOS_2022", ascending=True)
                .tail(10)
            )
            fig_causas = px.bar(
                df_causas_agg,
                x="OBITOS_2022",
                y="CAUSA_CID10",
                orientation="h",
                text="OBITOS_2022",
                color="OBITOS_2022",
                color_continuous_scale="Reds",
                labels={
                    "OBITOS_2022": "Óbitos em 2022",
                    "CAUSA_CID10": "Capítulo CID-10 (Causa do Óbito)",
                },
                title="Top 10 Principais Causas de Mortalidade em 2022 (Capítulos CID-10)",
                height=430,
            )
            fig_causas.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig_causas.update_layout(yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_causas, width="stretch")

        st.divider()
        st.subheader(
            "📚 Pobreza, Desigualdade (Gini), IDH Municipal e Evolução do IDEB (2005–2025)"
        )

        ed1, ed2 = st.columns(2)
        with ed1:
            df_ideb_f = df_ideb_hist[
                df_ideb_hist["MUNICIPIO_CHAVE"].isin(chaves_filtradas)
            ]
            df_ideb_serie = (
                df_ideb_f.groupby(["ANO", "ETAPA"], as_index=False)["IDEB"]
                .mean()
                .round(2)
            )
            fig_ideb = px.line(
                df_ideb_serie,
                x="ANO",
                y="IDEB",
                color="ETAPA",
                markers=True,
                text="IDEB",
                labels={
                    "ANO": "Ano de Avaliação",
                    "IDEB": "Nota Média do IDEB",
                    "ETAPA": "Etapa de Ensino",
                },
                title="Evolução Média do IDEB nos Municípios em Exibição (2005–2025)",
                height=420,
            )
            fig_ideb.update_traces(textposition="top center")
            st.plotly_chart(fig_ideb, width="stretch")

        with ed2:
            df_pob_reg = (
                df_filtrado.groupby(col_regiao, as_index=False)
                .agg(
                    INCIDENCIA_POBREZA_PCT=("INCIDENCIA_POBREZA_PCT", "mean"),
                    IDH_1991=("IDH_1991", "mean"),
                    IDH_2000=("IDH_2000", "mean"),
                    IDH_2010=("IDH_2010", "mean"),
                )
                .round(3)
            )
            df_idh_melt = df_pob_reg.melt(
                id_vars=[col_regiao],
                value_vars=["IDH_1991", "IDH_2000", "IDH_2010"],
                var_name="CENSO_IDH",
                value_name="IDH_MEDIO",
            )
            df_idh_melt["CENSO_IDH"] = df_idh_melt["CENSO_IDH"].str.replace(
                "IDH_", "Ano "
            )
            fig_idh = px.bar(
                df_idh_melt,
                x=col_regiao,
                y="IDH_MEDIO",
                color="CENSO_IDH",
                barmode="group",
                text="IDH_MEDIO",
                labels={
                    col_regiao: tipo_regiao_label,
                    "IDH_MEDIO": "IDH Municipal Médio",
                    "CENSO_IDH": "Ano de Referência",
                },
                title=f"Evolução Histórica do IDH Municipal Médio por {tipo_regiao_label} (1991, 2000 e 2010)",
                height=420,
            )
            fig_idh.update_traces(texttemplate="%{text:.3f}", textposition="outside")
            st.plotly_chart(fig_idh, width="stretch")

    # =========================================================================
    # ABA 4: VALIDAÇÃO DE COERÊNCIA, AUDITORIA & BASE DE DADOS ENRIQUECIDA
    # =========================================================================
    with aba_coerencia:
        st.subheader(
            "✅ Validação de Coerência e Coesão dos Dados: Há municípios com mais atendimentos que habitantes?"
        )

        if auditoria["ha_municipios_com_mais_atendimentos_que_habitantes"]:
            st.error(
                f"Foram identificados {auditoria['qtd_municipios_mais_atendimentos_que_habitantes']} "
                "municípios com mais atendimentos que habitantes."
            )
        else:
            st.success(
                "✔️ **Coesão e Coerência Confirmadas (100% Válido):** **NÃO há nenhum município com mais atendimentos "
                "que habitantes** em todo o estado do Ceará (`0 de 184 municípios`).\n\n"
                "- **Maior cobertura proporcional:** **Penaforte**, com **753 atendimentos** para **8.972 habitantes** "
                "(`8,39%` da população residente, ou `8.392,78` atendimentos por 100 mil hab.).\n"
                "- **Menor cobertura proporcional:** **Fortaleza**, com **9.364 atendimentos** para **2.428.708 habitantes** "
                "(`0,39%` da população residente, ou `385,55` atendimentos por 100 mil hab.)."
            )

        val1, val2 = st.columns(2)
        with val1:
            df_maior_prop_15 = df_filtrado.sort_values(
                "PROPORCAO_POP_ATENDIDA_PCT", ascending=False
            ).head(15)
            fig_coerencia = go.Figure()
            fig_coerencia.add_trace(
                go.Bar(
                    name="Atendimentos SUS (IDs Únicos)",
                    x=df_maior_prop_15["MUNICIPIO"],
                    y=df_maior_prop_15["TOTAL_ATENDIMENTOS"],
                    marker_color="#2563eb",
                )
            )
            fig_coerencia.add_trace(
                go.Bar(
                    name="População Residente (Censo 2022)",
                    x=df_maior_prop_15["MUNICIPIO"],
                    y=df_maior_prop_15["POPULACAO_2022"],
                    marker_color="#94a3b8",
                )
            )
            fig_coerencia.update_layout(
                barmode="group",
                title="Comparativo Direto: Atendimentos vs. População (Top 15 Maior Cobertura %)",
                xaxis_title="Município",
                yaxis_title="Quantidade (Pessoas / Atendimentos)",
                height=430,
            )
            st.plotly_chart(fig_coerencia, width="stretch")

        with val2:
            df_top_nomes = pd.DataFrame(
                auditoria["top_20_primeiros_nomes"]
            ).sort_values("atendimentos", ascending=True)
            fig_nomes = px.bar(
                df_top_nomes,
                x="atendimentos",
                y="primeiro_nome",
                orientation="h",
                text="atendimentos",
                color="atendimentos",
                color_continuous_scale="Purples",
                labels={
                    "primeiro_nome": "Primeiro Nome",
                    "atendimentos": "Quantidade de Atendimentos (IDs distintos)",
                },
                title="Por que NÃO agrupar por Nome? Top 20 Primeiros Nomes em Atendimentos (IDs)",
                height=430,
            )
            fig_nomes.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig_nomes.update_layout(yaxis_title=None, showlegend=False)
            st.plotly_chart(fig_nomes, width="stretch")

        st.markdown(
            "#### 🛠️ Resumo da Auditoria de Qualidade e Padronização dos Dados de Entrada"
        )
        aud1, aud2, aud3, aud4 = st.columns(4)
        aud1.metric(
            "IDs Únicos Validados",
            formatar_int(auditoria["total_atendimentos_unicos_id"]),
            f"Nulos: {auditoria['ids_nulos']} | Duplicados: {auditoria['ids_duplicados']}",
        )
        aud2.metric(
            "Espaços Extras Removidos",
            formatar_int(auditoria["registros_com_espacos_extras_municipio"]),
            "Padding de 100 caracteres em MUNICÍPIO",
        )
        aud3.metric(
            "Divergências de Grafia IBGE",
            "2 municípios corrigidos",
            "ITAPAGÉ ➔ Itapajé | ERERÊ ➔ Ereré",
        )
        aud4.metric(
            "Nomes com Ruído Corrigidos",
            f"{auditoria['nomes_com_ruido_corrigidos']} registros",
            "Caractere U+FFFD () e dígito '0' (J0SE)",
        )

        st.divider()
        st.subheader("📥 Base Consolidada Enriquecida por Município")

        colunas_exibicao = [
            "CODIGO_IBGE",
            "MUNICIPIO",
            "MACRORREGIAO_SAUDE",
            "MESORREGIAO",
            "TOTAL_ATENDIMENTOS",
            "POPULACAO_2022",
            "ATENDIMENTOS_POR_100K_HAB",
            "PROPORCAO_POP_ATENDIDA_PCT",
            "MAIS_ATENDIMENTOS_QUE_HABITANTES",
            "SALDO_HABITANTES_MENOS_ATENDIMENTOS",
            "IDH_2010",
            "INCIDENCIA_POBREZA_PCT",
            "INDICE_GINI",
            "OBITOS_2022",
            "TAXA_MORTALIDADE_1000_HAB",
            "IDEB_AI_2023",
            "PCT_AGUA_REDE_GERAL",
            "PCT_ESGOTO_REDE_OU_FOSSA",
        ]
        st.dataframe(
            df_filtrado[colunas_exibicao].sort_values(
                "ATENDIMENTOS_POR_100K_HAB", ascending=False
            ),
            width="stretch",
            height=420,
        )

        csv_bytes = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar Base Municipal Enriquecida (.CSV)",
            data=csv_bytes,
            file_name="municipios_ceara_enriquecidos_sus_ibge.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader(
            "🔎 Amostra da Base Individual de Atendimentos Enriquecida (`DADOS.txt` + IBGE)"
        )
        chaves_atuais = tuple(sorted(df_filtrado["MUNICIPIO_CHAVE"].unique().tolist()))
        df_amostra_atend = carregar_amostra_atendimentos(
            chaves_atuais if len(chaves_atuais) < 184 else None, limite=500
        )
        st.dataframe(df_amostra_atend, width="stretch", height=320)
