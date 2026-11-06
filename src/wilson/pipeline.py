"""Pipeline de tratamento, padronização, validação de coerência e enriquecimento de dados."""

from __future__ import annotations

import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from wilson.geo_ceara import MUNICIPIOS_CEARA_GEO

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "data_enriched"


def normalizar_chave_municipio(nome: str) -> str:
    """Padroniza o nome do município para chave de junção (maiúsculo, sem espaços extras, sem acentos).

    Trata divergências históricas de grafia entre a base DADOS.txt e o IBGE:
    - 'ITAPAGÉ' (DADOS.txt) -> 'ITAPAJE' ('Itapajé' no IBGE)
    - 'ERERÊ' (DADOS.txt) -> 'ERERE' ('Ereré' no IBGE)
    """
    limpo = unicodedata.normalize("NFKD", nome.strip().upper())
    sem_acento = "".join(c for c in limpo if not unicodedata.combining(c))
    if sem_acento == "ITAPAGE":
        return "ITAPAJE"
    return sem_acento


def tratar_primeiro_nome(nome_bruto: str) -> tuple[str, bool]:
    """Padroniza o primeiro nome, removendo espaços e corrigindo corrupções de encoding (U+FFFD) e dígitos."""
    limpo = nome_bruto.strip().upper()
    teve_ruido = False

    if "\ufffd" in limpo:
        teve_ruido = True
        if limpo == "\ufffdTILA":
            limpo = "ATILA"
        else:
            limpo = limpo.replace("\ufffd", "").strip()

    if "0" in limpo:
        teve_ruido = True
        limpo = limpo.replace("0", "O")

    return limpo, teve_ruido


def parse_float(val: str) -> float | None:
    """Converte string numérica das bases do IBGE para float, tratando '-' e vazio como None."""
    v = val.strip()
    if not v or v == "-":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def carregar_censo_2022(caminho: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Extrai indicadores demográficos e domiciliares do Censo 2022 por município."""
    mapa_posicoes = {
        "1.1": "AREA_KM2",
        "1.2": "DENSIDADE_DEMOGRAFICA",
        "2": "POPULACAO_2022",
        "2.1.1": "POP_MASCULINA",
        "2.1.2": "POP_FEMININA",
        "2.1.3": "RAZAO_SEXO",
        "2.2.1": "IDADE_MEDIANA",
        "2.2.2": "INDICE_ENVELHECIMENTO",
        "2.2.3": "POP_0_A_14_ANOS",
        "2.2.4": "POP_60_MAIS_ANOS",
        "2.3.1": "POP_BRANCA",
        "2.3.2": "POP_PRETA",
        "2.3.3": "POP_AMARELA",
        "2.3.4": "POP_PARDA",
        "2.3.5": "POP_INDIGENA_RACA",
        "2.4": "TAXA_CRESCIMENTO_GEOMETRICO_PCT",
        "2.5": "VARIACAO_ABSOLUTA_POP_2010_2022",
        "3.1": "DOMICILIOS_RECENSEADOS",
        "3.2": "DOMICILIOS_OCUPADOS",
        "3.2.2.1.1.1": "PCT_AGUA_REDE_GERAL",
        "3.2.3.1.1": "PCT_ESGOTO_REDE_OU_FOSSA",
        "3.2.4.1.1": "PCT_LIXO_COLETADO",
        "3.2.5.1.1": "PCT_BANHEIRO_EXCLUSIVO",
        "3.2.6.1": "MEDIA_MORADORES_DOMICILIO",
        "4": "POP_INDIGENA_TOTAL",
        "5": "POP_QUILOMBOLA_TOTAL",
    }

    dados: dict[str, dict[str, Any]] = {}
    nomes_ibge: dict[str, str] = {}

    with open(caminho, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 4 or not row[2].strip():
                continue
            pos, _, loc, val_2022 = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            chave = normalizar_chave_municipio(loc)
            nomes_ibge[chave] = loc
            if pos in mapa_posicoes:
                col = mapa_posicoes[pos]
                dados.setdefault(chave, {})[col] = parse_float(val_2022)

    return dados, nomes_ibge


def carregar_pobreza_desigualdade(caminho: Path) -> dict[str, dict[str, Any]]:
    """Extrai indicadores do Mapa de Pobreza e Desigualdade (IBGE)."""
    mapa_posicoes = {
        "1": "INCIDENCIA_POBREZA_PCT",
        "1.1": "INCIDENCIA_POBREZA_LIM_INF_PCT",
        "1.2": "INCIDENCIA_POBREZA_LIM_SUP_PCT",
        "2": "INCIDENCIA_POBREZA_SUBJETIVA_PCT",
        "3": "INDICE_GINI",
        "3.1": "INDICE_GINI_LIM_INF",
        "3.2": "INDICE_GINI_LIM_SUP",
    }
    dados: dict[str, dict[str, Any]] = {}
    with open(caminho, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 4 or not row[2].strip():
                continue
            pos, loc, val = row[0].strip(), row[2].strip(), row[3].strip()
            if pos in mapa_posicoes:
                chave = normalizar_chave_municipio(loc)
                dados.setdefault(chave, {})[mapa_posicoes[pos]] = parse_float(val)
    return dados


def carregar_idh(caminho: Path) -> dict[str, dict[str, Any]]:
    """Extrai o IDH Municipal (1991, 2000, 2010) e calcula a evolução."""
    dados: dict[str, dict[str, Any]] = {}
    with open(caminho, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 6 or not row[2].strip():
                continue
            loc = row[2].strip()
            chave = normalizar_chave_municipio(loc)
            idh_1991 = parse_float(row[3])
            idh_2000 = parse_float(row[4])
            idh_2010 = parse_float(row[5])
            evolucao_pct = (
                round(((idh_2010 - idh_1991) / idh_1991) * 100, 2)
                if idh_1991 and idh_2010
                else None
            )
            dados[chave] = {
                "IDH_1991": idh_1991,
                "IDH_2000": idh_2000,
                "IDH_2010": idh_2010,
                "EVOLUCAO_IDH_1991_2010_PCT": evolucao_pct,
            }
    return dados


def carregar_ideb(
    caminho: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Extrai o IDEB (Anos Iniciais e Anos Finais da Rede Pública) de 2005 a 2025."""
    dados: dict[str, dict[str, Any]] = {}
    historico: list[dict[str, Any]] = []

    with open(caminho, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        anos = [col.strip() for col in header[3:14]]  # 2005..2025

        for row in reader:
            if len(row) < 14 or not row[2].strip():
                continue
            pos = row[0].strip()
            loc = row[2].strip()
            chave = normalizar_chave_municipio(loc)

            if pos in ("1.1.1.1", "1.1.2.1"):
                etapa = "Anos Iniciais (Pública)" if pos == "1.1.1.1" else "Anos Finais (Pública)"
                prefixo = "IDEB_AI" if pos == "1.1.1.1" else "IDEB_AF"
                for idx, ano in enumerate(anos):
                    valor = parse_float(row[3 + idx])
                    if ano in ("2019", "2021", "2023", "2025"):
                        dados.setdefault(chave, {})[f"{prefixo}_{ano}"] = valor
                    if valor is not None:
                        historico.append(
                            {
                                "MUNICIPIO_CHAVE": chave,
                                "MUNICIPIO": loc,
                                "ETAPA": etapa,
                                "ANO": int(ano),
                                "IDEB": valor,
                            }
                        )
    return dados, historico


def carregar_mortalidade(
    caminho: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Extrai série histórica de óbitos (2006-2022), mortalidade infantil e causas CID-10."""
    causas_posicoes = {
        "1.3.1": "Doenças infecciosas e parasitárias",
        "1.3.2": "Neoplasmas (Tumores)",
        "1.3.4": "Doenças endócrinas, nutricionais e metabólicas",
        "1.3.5": "Transtornos mentais e comportamentais",
        "1.3.6": "Doenças do sistema nervoso",
        "1.3.9": "Doenças do aparelho circulatório",
        "1.3.10": "Doenças do aparelho respiratório",
        "1.3.11": "Doenças do aparelho digestivo",
        "1.3.14": "Doenças do aparelho geniturinário",
        "1.3.15": "Gravidez, parto e puerpério",
        "1.3.16": "Afecções originadas no período perinatal",
        "1.3.17": "Malformações congênitas",
        "1.3.18": "Sintomas e sinais mal definidos",
        "1.3.20": "Causas externas de morbidade e mortalidade",
    }

    dados: dict[str, dict[str, Any]] = {}
    historico_obitos: list[dict[str, Any]] = []
    causas_2022: list[dict[str, Any]] = []

    with open(caminho, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        anos = [col.strip() for col in header[3:20]]  # 2006..2022

        for row in reader:
            if len(row) < 20 or not row[2].strip():
                continue
            pos = row[0].strip()
            loc = row[2].strip()
            chave = normalizar_chave_municipio(loc)
            valores_anos = [parse_float(row[3 + i]) or 0.0 for i in range(len(anos))]
            val_2022 = valores_anos[-1]

            if pos == "1":
                dados.setdefault(chave, {})["OBITOS_2022"] = int(val_2022)
                dados[chave]["OBITOS_2021"] = int(valores_anos[-2])
                dados[chave]["OBITOS_2020"] = int(valores_anos[-3])
                dados[chave]["OBITOS_2019"] = int(valores_anos[-4])
                dados[chave]["OBITOS_TOTAL_2006_2022"] = int(sum(valores_anos))
                for ano, v in zip(anos, valores_anos):
                    historico_obitos.append(
                        {
                            "MUNICIPIO_CHAVE": chave,
                            "MUNICIPIO": loc,
                            "ANO": int(ano),
                            "OBITOS": int(v),
                        }
                    )
            elif pos == "1.1.1":
                dados.setdefault(chave, {})["OBITOS_MASCULINO_2022"] = int(val_2022)
            elif pos == "1.1.2":
                dados.setdefault(chave, {})["OBITOS_FEMININO_2022"] = int(val_2022)
            elif pos == "1.2.1":
                dados.setdefault(chave, {})["OBITOS_MENOS_1_ANO_2022"] = int(val_2022)
            elif pos in causas_posicoes:
                nome_causa = causas_posicoes[pos]
                causas_2022.append(
                    {
                        "MUNICIPIO_CHAVE": chave,
                        "MUNICIPIO": loc,
                        "POSICAO_CID": pos,
                        "CAUSA_CID10": nome_causa,
                        "OBITOS_2022": int(val_2022),
                        "OBITOS_ACUMULADOS_2006_2022": int(sum(valores_anos)),
                    }
                )
                if pos == "1.3.9":
                    dados.setdefault(chave, {})["OBITOS_CIRCULATORIO_2022"] = int(val_2022)
                elif pos == "1.3.2":
                    dados.setdefault(chave, {})["OBITOS_NEOPLASMAS_2022"] = int(val_2022)
                elif pos == "1.3.10":
                    dados.setdefault(chave, {})["OBITOS_RESPIRATORIO_2022"] = int(val_2022)
                elif pos == "1.3.20":
                    dados.setdefault(chave, {})["OBITOS_CAUSAS_EXTERNAS_2022"] = int(val_2022)
                elif pos == "1.3.1":
                    dados.setdefault(chave, {})["OBITOS_INFECCIOSAS_2022"] = int(val_2022)

    return dados, historico_obitos, causas_2022


def executar_enriquecimento() -> dict[str, Any]:
    """Executa todo o pipeline de tratamento, junção, validação e enriquecimento de dados."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Carregar bases do IBGE
    censo, nomes_ibge = carregar_censo_2022(BASE_DIR / "Censo 2022 (2022).csv")
    pobreza = carregar_pobreza_desigualdade(BASE_DIR / "Mapa de pobreza e desigualdade.csv")
    idh = carregar_idh(BASE_DIR / "Índice de Desenvolvimento Humano municipal.csv")
    ideb, ideb_hist = carregar_ideb(
        BASE_DIR / "Índice de Desenvolvimento da Educação Básica.csv"
    )
    mortalidade, mort_hist, mort_causas = carregar_mortalidade(BASE_DIR / "Mortalidade.csv")

    # 2. Ler, tratar e auditar DADOS.txt (Base de Atendimentos SUS)
    contagem_atendimentos: Counter[str] = Counter()
    nomes_distintos_por_mun: dict[str, set[str]] = {}
    nomes_frequencia_global: Counter[str] = Counter()
    municipios_brutos_dados: dict[str, str] = {}

    registros_atendimentos: list[dict[str, Any]] = []
    ids_vistos: set[int] = set()
    ids_duplicados = 0
    ids_nulos = 0
    nomes_corrigidos = 0
    espacos_removidos_mun = 0

    caminho_dados = BASE_DIR / "DADOS.txt"
    with open(caminho_dados, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        _ = next(reader)  # ID,MUNICÍPIO,PRIMEIRO_NOME
        for row in reader:
            if not row:
                continue
            id_str = row[0].strip()
            mun_bruto = row[1]
            nome_bruto = row[2] if len(row) > 2 else ""

            if len(mun_bruto) != len(mun_bruto.strip()):
                espacos_removidos_mun += 1

            if not id_str:
                ids_nulos += 1
                continue

            id_int = int(id_str)
            if id_int in ids_vistos:
                ids_duplicados += 1
            ids_vistos.add(id_int)

            mun_limpo = mun_bruto.strip().upper()
            chave_mun = normalizar_chave_municipio(mun_limpo)
            municipios_brutos_dados[chave_mun] = mun_limpo

            nome_tratado, teve_ruido = tratar_primeiro_nome(nome_bruto)
            if teve_ruido:
                nomes_corrigidos += 1

            # Cada ID é contabilizado como um atendimento distinto (sem deduplicar por PRIMEIRO_NOME)
            contagem_atendimentos[chave_mun] += 1
            nomes_distintos_por_mun.setdefault(chave_mun, set()).add(nome_tratado)
            nomes_frequencia_global[nome_tratado] += 1

            registros_atendimentos.append(
                {
                    "ID": id_int,
                    "MUNICIPIO_ORIGINAL": mun_limpo,
                    "MUNICIPIO_CHAVE": chave_mun,
                    "PRIMEIRO_NOME_ORIGINAL": nome_bruto.strip(),
                    "PRIMEIRO_NOME": nome_tratado,
                }
            )

    # 3. Construir tabela consolidada de municípios enriquecidos
    linhas_municipios: list[dict[str, Any]] = []
    todas_chaves = sorted(nomes_ibge.keys())

    for chave in todas_chaves:
        cod_ibge, mesorregiao, macrorregiao_saude, lat, lon = MUNICIPIOS_CEARA_GEO[chave]
        nome_oficial = nomes_ibge[chave]
        nome_dados = municipios_brutos_dados.get(chave, nome_oficial.upper())

        total_atend = contagem_atendimentos.get(chave, 0)
        qtd_nomes_distintos = len(nomes_distintos_por_mun.get(chave, set()))

        dados_censo = censo.get(chave, {})
        dados_pob = pobreza.get(chave, {})
        dados_idh = idh.get(chave, {})
        dados_ideb = ideb.get(chave, {})
        dados_mort = mortalidade.get(chave, {})

        pop = dados_censo.get("POPULACAO_2022") or 0.0
        area = dados_censo.get("AREA_KM2") or 0.0
        obitos_2022 = dados_mort.get("OBITOS_2022") or 0

        atend_por_100k = round((total_atend / pop) * 100_000, 2) if pop > 0 else 0.0
        prop_pop_atendida_pct = round((total_atend / pop) * 100, 2) if pop > 0 else 0.0
        atend_por_km2 = round(total_atend / area, 2) if area > 0 else 0.0
        taxa_mortalidade_1000 = round((obitos_2022 / pop) * 1_000, 2) if pop > 0 else 0.0
        mais_atend_que_hab = bool(total_atend > pop)
        razao_repeticao_nomes = (
            round(total_atend / qtd_nomes_distintos, 2) if qtd_nomes_distintos > 0 else 1.0
        )

        linha: dict[str, Any] = {
            "CODIGO_IBGE": cod_ibge,
            "MUNICIPIO": nome_oficial,
            "MUNICIPIO_DADOS_TXT": nome_dados,
            "MUNICIPIO_CHAVE": chave,
            "MESORREGIAO": mesorregiao,
            "MACRORREGIAO_SAUDE": macrorregiao_saude,
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "TOTAL_ATENDIMENTOS": total_atend,
            "NOMES_DISTINTOS": qtd_nomes_distintos,
            "MEDIA_ATENDIMENTOS_POR_NOME": razao_repeticao_nomes,
            "POPULACAO_2022": int(pop),
            "AREA_KM2": area,
            "DENSIDADE_DEMOGRAFICA": dados_censo.get("DENSIDADE_DEMOGRAFICA"),
            "ATENDIMENTOS_POR_100K_HAB": atend_por_100k,
            "PROPORCAO_POP_ATENDIDA_PCT": prop_pop_atendida_pct,
            "ATENDIMENTOS_POR_KM2": atend_por_km2,
            "MAIS_ATENDIMENTOS_QUE_HABITANTES": mais_atend_que_hab,
            "SALDO_HABITANTES_MENOS_ATENDIMENTOS": int(pop - total_atend),
            "TAXA_MORTALIDADE_1000_HAB": taxa_mortalidade_1000,
        }

        # Adicionar demais colunas de Censo, Pobreza, IDH, IDEB e Mortalidade
        for k, v in dados_censo.items():
            if k not in linha:
                linha[k] = v
        linha.update(dados_pob)
        linha.update(dados_idh)
        linha.update(dados_ideb)
        linha.update(dados_mort)

        linhas_municipios.append(linha)

    df_municipios = pd.DataFrame(linhas_municipios)

    # Calcular rankings
    df_municipios["RANK_VOLUME_ABSOLUTO"] = (
        df_municipios["TOTAL_ATENDIMENTOS"].rank(ascending=False, method="min").astype(int)
    )
    df_municipios["RANK_PROPORCIONAL_100K"] = (
        df_municipios["ATENDIMENTOS_POR_100K_HAB"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    df_municipios = df_municipios.sort_values("MUNICIPIO").reset_index(drop=True)

    # Salvar base municipal enriquecida
    df_municipios.to_csv(OUTPUT_DIR / "municipios_enriquecidos.csv", index=False)
    df_municipios.to_parquet(OUTPUT_DIR / "municipios_enriquecidos.parquet", index=False)

    # 4. Enriquecer a base individual de atendimentos (DADOS.txt + dados chave do município)
    colunas_join_atend = [
        "MUNICIPIO_CHAVE",
        "CODIGO_IBGE",
        "MUNICIPIO",
        "MESORREGIAO",
        "MACRORREGIAO_SAUDE",
        "LATITUDE",
        "LONGITUDE",
        "POPULACAO_2022",
        "ATENDIMENTOS_POR_100K_HAB",
        "INCIDENCIA_POBREZA_PCT",
        "INDICE_GINI",
        "IDH_2010",
        "IDEB_AI_2023",
        "OBITOS_2022",
        "TAXA_MORTALIDADE_1000_HAB",
    ]
    df_atendimentos = pd.DataFrame(registros_atendimentos)
    df_atendimentos_enriq = df_atendimentos.merge(
        df_municipios[colunas_join_atend],
        on="MUNICIPIO_CHAVE",
        how="left",
    )
    df_atendimentos_enriq.to_parquet(
        OUTPUT_DIR / "atendimentos_enriquecidos.parquet", index=False
    )
    df_atendimentos_enriq.to_csv(
        OUTPUT_DIR / "atendimentos_enriquecidos.csv", index=False
    )

    # 5. Salvar séries históricas auxiliares com metadados regionais
    mapa_regiao = df_municipios.set_index("MUNICIPIO_CHAVE")[
        ["CODIGO_IBGE", "MESORREGIAO", "MACRORREGIAO_SAUDE", "POPULACAO_2022"]
    ]

    df_mort_hist = pd.DataFrame(mort_hist).merge(
        mapa_regiao, on="MUNICIPIO_CHAVE", how="left"
    )
    df_mort_hist.to_csv(OUTPUT_DIR / "mortalidade_historico.csv", index=False)

    df_mort_causas = pd.DataFrame(mort_causas).merge(
        mapa_regiao, on="MUNICIPIO_CHAVE", how="left"
    )
    df_mort_causas.to_csv(OUTPUT_DIR / "mortalidade_causas_2022.csv", index=False)

    df_ideb_hist = pd.DataFrame(ideb_hist).merge(
        mapa_regiao, on="MUNICIPIO_CHAVE", how="left"
    )
    df_ideb_hist.to_csv(OUTPUT_DIR / "ideb_historico.csv", index=False)

    # 6. Gerar relatório de auditoria e validação de coerência
    mun_mais_atend_que_hab = df_municipios[
        df_municipios["MAIS_ATENDIMENTOS_QUE_HABITANTES"]
    ]["MUNICIPIO"].tolist()

    top_nomes = [
        {"primeiro_nome": nome, "atendimentos": qtd}
        for nome, qtd in nomes_frequencia_global.most_common(20)
    ]

    auditoria = {
        "total_atendimentos_unicos_id": len(df_atendimentos),
        "ids_nulos": ids_nulos,
        "ids_duplicados": ids_duplicados,
        "municipios_dados_txt": len(municipios_brutos_dados),
        "municipios_ibge": len(nomes_ibge),
        "municipios_pareados_sucesso": int(df_municipios["CODIGO_IBGE"].notna().sum()),
        "registros_com_espacos_extras_municipio": espacos_removidos_mun,
        "nomes_com_ruido_corrigidos": nomes_corrigidos,
        "divergencias_grafia_tratadas": [
            {"dados_txt": "ITAPAGÉ", "ibge": "Itapajé", "chave": "ITAPAJE"},
            {"dados_txt": "ERERÊ", "ibge": "Ereré", "chave": "ERERE"},
        ],
        "ha_municipios_com_mais_atendimentos_que_habitantes": len(mun_mais_atend_que_hab) > 0,
        "qtd_municipios_mais_atendimentos_que_habitantes": len(mun_mais_atend_que_hab),
        "lista_municipios_mais_atendimentos_que_habitantes": mun_mais_atend_que_hab,
        "maior_proporcao_municipio": df_municipios.sort_values(
            "ATENDIMENTOS_POR_100K_HAB", ascending=False
        )
        .iloc[0][
            [
                "MUNICIPIO",
                "TOTAL_ATENDIMENTOS",
                "POPULACAO_2022",
                "ATENDIMENTOS_POR_100K_HAB",
                "PROPORCAO_POP_ATENDIDA_PCT",
            ]
        ]
        .to_dict(),
        "menor_proporcao_municipio": df_municipios.sort_values(
            "ATENDIMENTOS_POR_100K_HAB", ascending=True
        )
        .iloc[0][
            [
                "MUNICIPIO",
                "TOTAL_ATENDIMENTOS",
                "POPULACAO_2022",
                "ATENDIMENTOS_POR_100K_HAB",
                "PROPORCAO_POP_ATENDIDA_PCT",
            ]
        ]
        .to_dict(),
        "top_20_primeiros_nomes": top_nomes,
    }

    with open(OUTPUT_DIR / "relatorio_auditoria.json", mode="w", encoding="utf-8") as f:
        json.dump(auditoria, f, ensure_ascii=False, indent=2)

    return auditoria


if __name__ == "__main__":
    resultado = executar_enriquecimento()
    print("Enriquecimento concluído com sucesso!")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

