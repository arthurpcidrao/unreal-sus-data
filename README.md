# 🏥 Wilson — Enriquecimento de Dados SUS & IBGE (Ceará) e Dashboard BI

Projeto de tratamento, padronização, validação de coerência e enriquecimento da base de atendimentos do SUS ([`DADOS.txt`](file:///home/arthurpcidrao/projetos/wilson/DADOS.txt)) integrada às bases demográficas, epidemiológicas, educacionais e socioeconômicas do **IBGE** para os **184 municípios do Ceará**, com visualização interativa em **Streamlit** gerenciada via **UV**.

---

## 🚀 Como Executar o Projeto (com `uv`)

### 1. Instalar / sincronizar dependências
```bash
uv sync
```

### 2. Executar o pipeline de tratamento e enriquecimento de dados
```bash
uv run wilson
```
*(Ou diretamente via `uv run python src/wilson/pipeline.py`. Os arquivos enriquecidos são gerados automaticamente no diretório `data_enriched/`).*

### 3. Iniciar o Dashboard BI Interativo no Streamlit
```bash
uv run streamlit run app.py
```

---

## 📂 Estrutura do Repositório

- [`app.py`](file:///home/arthurpcidrao/projetos/wilson/app.py): Ponto de entrada da aplicação Streamlit.
- [`src/wilson/pipeline.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/pipeline.py): Pipeline de limpeza, normalização de chaves municipais, enriquecimento com as 5 bases do IBGE, validação de coerência e exportação em CSV/Parquet.
- [`src/wilson/geo_ceara.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/geo_ceara.py): Mapeamento oficial dos 184 municípios do Ceará com Código IBGE (7 dígitos), Mesorregião IBGE, Macrorregião de Saúde do SUS e coordenadas geográficas (`LATITUDE`, `LONGITUDE`).
- [`src/wilson/dashboard.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/dashboard.py): Interface completa do Dashboard BI com 4 abas temáticas, filtros globais, mapa interativo de bolhas e análises cruzadas.
- [`DOCUMENTACAO_DASHBOARD.md`](file:///home/arthurpcidrao/projetos/wilson/DOCUMENTACAO_DASHBOARD.md): Documento auxiliar detalhando o funcionamento de cada gráfico, fórmula matemática, tratamento de dados e parâmetro do painel.
- `data_enriched/`: Diretório gerado pelo pipeline contendo:
  - `municipios_enriquecidos.csv` e `.parquet` (base consolidada dos 184 municípios com todos os indicadores).
  - `atendimentos_enriquecidos.csv` e `.parquet` (os 204.579 registros de `DADOS.txt` enriquecidos com os dados do respectivo município).
  - `mortalidade_historico.csv`, `mortalidade_causas_2022.csv`, `ideb_historico.csv` e `relatorio_auditoria.json`.

