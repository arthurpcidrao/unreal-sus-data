# 📊 Documentação Técnica, Análise de Insights e Roteiro de Apresentação — BI Atendimentos SUS & IBGE (Ceará)

Este documento reúne:
1. A descrição técnica de **como foi feito o enriquecimento dos dados** e a **filtragem/limpeza da base de entrada** ([`DADOS.txt`](file:///home/arthurpcidrao/projetos/wilson/DADOS.txt)).
2. O funcionamento dos **parâmetros e gráficos interativos** do Dashboard em Streamlit ([`app.py`](file:///home/arthurpcidrao/projetos/wilson/app.py) / [`src/wilson/dashboard.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/dashboard.py)).
3. O **bloco completo de métricas, tabelas de maiores e menores valores do estado e insights estatísticos** extraídos das bases (incluindo o cruzamento entre **Atendimentos vs. Mortalidade vs. IDH vs. Pobreza**, médias estaduais do Ceará, rankings completos e análise espacial).
4. A **separação estruturada dos slides** para apresentação da equipe (**Arthur, Braule, Lucas, Guilherme, Eduardo**).

---

## 1. Como Foi Feito o Enriquecimento dos Dados

O pipeline de engenharia de dados implementado em [`src/wilson/pipeline.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/pipeline.py) parte da base transacional de referência [`DADOS.txt`](file:///home/arthurpcidrao/projetos/wilson/DADOS.txt) (`204.579` registros com as colunas `ID`, `MUNICÍPIO`, `PRIMEIRO_NOME`) e executa o enriquecimento em 4 camadas:

1. **Criação da Chave Padronizada de Junção (`MUNICIPIO_CHAVE`):**
   - Como as bases em CSV não traziam originalmente a coluna de código numérico do município, utilizou-se o nome do município normalizado (caixa alta, sem espaços laterais e sem acentos via decomposição Unicode `NFKD`) como chave de ligação ([`normalizar_chave_municipio`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/pipeline.py#L19-L30)).
   - Para garantir **100% de integridade referencial**, o dicionário geográfico [`src/wilson/geo_ceara.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/geo_ceara.py) adicionou a cada município o seu **Código Oficial do IBGE de 7 dígitos (`CODIGO_IBGE`)**, a **Macrorregião de Saúde do SUS Ceará**, a **Mesorregião do IBGE** e as **coordenadas geográficas exatas da sede municipal (`LATITUDE`, `LONGITUDE`)**.
2. **Extração e Pivotamento das 5 Bases Oficiais do IBGE:**
   - As bases do IBGE possuem estrutura hierárquica (`Posição`, `Nome`, `Localidade`, `Anos...`). O pipeline filtra apenas as linhas analíticas (que possuem `Localidade` preenchida) e converte cada posição hierárquica em colunas tipadas:
     - **[`Censo 2022 (2022).csv`](file:///home/arthurpcidrao/projetos/wilson/Censo%202022%20(2022).csv):** População residente (`POPULACAO_2022`), Área (`AREA_KM2`), Densidade demográfica (`DENSIDADE_DEMOGRAFICA`), sexo, cor/raça, idade mediana, índice de envelhecimento, domicílios e saneamento (% água via rede geral, % esgoto/fossa ligada à rede, % lixo coletado, % banheiro exclusivo).
     - **[`Mortalidade.csv`](file:///home/arthurpcidrao/projetos/wilson/Mortalidade.csv):** Série histórica anual de óbitos de **2006 a 2022** (`OBITOS_2022`, `OBITOS_TOTAL_2006_2022`), mortalidade infantil (`< 1 ano`) e óbitos por **Capítulos da CID-10** (doenças circulatórias, neoplasmas/tumores, respiratórias, causas externas, infecciosas, etc.).
     - **[`Mapa de pobreza e desigualdade.csv`](file:///home/arthurpcidrao/projetos/wilson/Mapa%20de%20pobreza%20e%20desigualdade.csv):** Incidência da pobreza (`INCIDENCIA_POBREZA_PCT`), pobreza subjetiva (`INCIDENCIA_POBREZA_SUBJETIVA_PCT`), **Índice de Gini** (`INDICE_GINI`) e intervalos de confiança.
     - **[`Índice de Desenvolvimento Humano municipal.csv`](file:///home/arthurpcidrao/projetos/wilson/%C3%8Dndice%20de%20Desenvolvimento%20Humano%20municipal.csv):** Série do IDH Municipal (`IDH_1991`, `IDH_2000`, `IDH_2010`) e variação percentual acumulada (`1991–2010`).
     - **[`Índice de Desenvolvimento da Educação Básica.csv`](file:///home/arthurpcidrao/projetos/wilson/%C3%8Dndice%20de%20Desenvolvimento%20da%20Educa%C3%A7%C3%A3o%20B%C3%A1sica.csv):** Série histórica bienal de **2005 a 2025** do IDEB da rede pública para Anos Iniciais (`IDEB_AI_*`) e Anos Finais (`IDEB_AF_*`).
3. **Cálculo de Indicadores Derivados Epidemiológicos e Demográficos:**
   - $\text{Atendimentos por 100 mil hab.} = \left(\frac{\text{Total de Atendimentos}}{\text{População 2022}}\right) \times 100.000$
   - $\text{Proporção da População Atendida (\%)} = \left(\frac{\text{Total de Atendimentos}}{\text{População 2022}}\right) \times 100$
   - $\text{Densidade Territorial de Atendimentos} = \frac{\text{Total de Atendimentos}}{\text{Área (km}^2\text{)}}$
   - $\text{Taxa Bruta de Mortalidade por 1.000 hab. (2022)} = \left(\frac{\text{Óbitos em 2022}}{\text{População 2022}}\right) \times 1.000$
4. **Materialização das Bases Enriquecidas (`data_enriched/`):**
   - [`municipios_enriquecidos.csv`](file:///home/arthurpcidrao/projetos/wilson/data_enriched/municipios_enriquecidos.csv) / `.parquet`: Tabela analítica consolidada com os **184 municípios** e 56 colunas enriquecidas.
   - [`atendimentos_enriquecidos.csv`](file:///home/arthurpcidrao/projetos/wilson/data_enriched/atendimentos_enriquecidos.csv) / `.parquet`: Os **204.579 atendimentos individuais** enriquecidos com os indicadores do respectivo município.

---

## 2. Como Foi Feita a Filtragem, Limpeza e Validação de Coerência

Durante a auditoria automatizada dos dados de entrada ([`relatorio_auditoria.json`](file:///home/arthurpcidrao/projetos/wilson/data_enriched/relatorio_auditoria.json)), foram identificados e tratados os seguintes pontos:

1. **Remoção de Espaços Extras (*Padding* de 100 caracteres):**
   - Todas as `204.579` linhas de [`DADOS.txt`](file:///home/arthurpcidrao/projetos/wilson/DADOS.txt) possuíam o campo `MUNICÍPIO` preenchido com espaços em branco até completar 100 caracteres (ex.: `"ABAIARA                                                                                             "`). Sem o `.strip()`, nenhuma chave casaria com os arquivos do IBGE.
2. **Reconciliação de Divergências Ortográficas entre `DADOS.txt` e IBGE:**
   - Dois municípios cearenses apresentavam grafias distintas entre a base do SUS e a base do IBGE:
     - Em `DADOS.txt`: **`ITAPAGÉ`** (com `G`) $\leftrightarrow$ No IBGE: **`Itapajé`** (com `J`).
     - Em `DADOS.txt`: **`ERERÊ`** (acento circunflexo) $\leftrightarrow$ No IBGE: **`Ereré`** (acento agudo).
   - Ambos foram normalizados na função [`normalizar_chave_municipio`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/pipeline.py#L19-L30), garantindo que **nenhum município ficasse órfão** (`184 de 184` municípios pareados com sucesso).
3. **Limpeza de Ruídos de Codificação em `PRIMEIRO_NOME`:**
   - Foram detectados **17 registros** com anomalias lexicais na coluna `PRIMEIRO_NOME`:
     - `16` registros continham o caractere de substituição Unicode `\ufffd` (``) oriundo de falha de codificação Latin-1/UTF-8 na origem: `MARIA` (2x), `ANA`, `BEATRIZ`, `BERNARDETE`, `CLEMILDA`, `DARLA`, `ERIVANIA`, `FABIANA`, `FRANCILEIDE`, `JOSEFA`, `LAIANE`, `GEISYLENE`, `ISABELE`, `JOEL` e `TILA` (corrigido para `ATILA`).
     - `1` registro continha o algarismo zero no lugar da letra O: `J0SE` (corrigido para `JOSE`).
4. **Preservação Estrita do `ID` como Unidade de Atendimento (Por que NÃO agrupar por `PRIMEIRO_NOME`):**
   - Verificou-se que os `204.579` registros possuem `ID`s sequenciais únicos (`1` a `204.579`), com **0 IDs nulos** e **0 IDs duplicados**.
   - Existem apenas **9.749 primeiros nomes distintos** em toda a base. Os 4 nomes mais comuns somam sozinhos **41,2% de todos os atendimentos do estado**:
     - `MARIA`: **48.242 atendimentos** (23,58% da base)
     - `FRANCISCA`: **14.179 atendimentos** (6,93% da base)
     - `ANTONIA`: **12.346 atendimentos** (6,03% da base)
     - `ANA`: **9.478 atendimentos** (4,63% da base)
   - Portanto, agrupar por `PRIMEIRO_NOME` descartaria indevidamente **95,2% dos atendimentos reais**. Toda a contagem do projeto utiliza exclusivamente o `ID` único.
5. **Tratamento de Valores Ausentes (`"-"`) nas Bases do IBGE:**
   - Nas tabelas do IBGE, valores não aplicáveis ou suprimidos são representados por `"-"`. Todos foram convertidos de forma segura para `None`/`NaN` nas métricas contínuas ou `0` em contagens de óbitos por causas específicas.
6. **Validação de Coerência Demográfica (*"Há municípios com mais atendimentos que habitantes?"*):**
   - Comparando `TOTAL_ATENDIMENTOS` com `POPULACAO_2022` (Censo 2022) para todos os 184 municípios:
   - **Resultado:** **NÃO há nenhum município com mais atendimentos que habitantes (`0 municípios`)**.
   - Mesmo o município com a maior cobertura proporcional do Ceará (**Penaforte**) registrou **753 atendimentos** para uma população de **8.972 habitantes** (`8,39%` da população atendida, restando um saldo positivo de `8.219` habitantes).

---

## 3. Insights Observados, Tabelas de Maiores e Menores Valores do Estado e Análise Estatística

### 3.1. Tabela Geral de Extremos do Estado (Médias, Medianas, Menores e Maiores Valores do Ceará)

Esta tabela sintetiza os **menores valores** e os **maiores valores** encontrados entre todos os **184 municípios do Ceará**, juntamente com a média e a mediana municipal de referência:

| Indicador Analisado | Média Municipal (184 mun.) | Mediana Municipal | 🔽 MENOR Valor no Estado (Município) | 🔼 MAIOR Valor no Estado (Município) | Total / Taxa Ponderada Estadual |
| :--- | :---: | :---: | :--- | :--- | :---: |
| **Volume de Atendimentos (`ID`s)** | `1.111,84` | `756,50` | **`39`** (*Ereré*) | **`9.364`** (*Fortaleza*) | **204.579 atendimentos** |
| **População Residente (2022)** | `47.798,68` | `20.913,50` | **`4.841`** (*Granjeiro*) | **`2.428.708`** (*Fortaleza*) | **8.794.957 habitantes** |
| **Atendimentos / 100 mil hab.** | **`3.624,82`** | **`3.371,86`** | **`385,55`** (*Fortaleza*) | **`8.392,78`** (*Penaforte*) | **2.326,09 / 100k hab.** |
| **% da População Atendida** | `3,62%` | `3,38%` | **`0,39%`** (*Fortaleza*) | **`8,39%`** (*Penaforte*) | **2,33% da pop. estadual** |
| **IDH Municipal (2010)** | **`0,617`** | **`0,612`** | **`0,540`** (*Salitre*) | **`0,754`** (*Fortaleza*) | Evolução de +103% desde 1991 (`0,304`) |
| **Incidência de Pobreza (%)** | **`60,18%`** | **`60,49%`** | **`35,02%`** (*São João do Jaguaribe*) | **`79,47%`** (*Saboeiro*) | — |
| **Índice de Gini (Desigualdade)** | `0,417` | `0,410` | **`0,370`** (*Itaiçaba*) | **`0,510`** (*Fortaleza*) | — |
| **Óbitos Totais em 2022** | `351,42` | `159,00` | **`38`** (*Granjeiro*) | **`17.826`** (*Fortaleza*) | **64.661 óbitos em 2022** |
| **Taxa de Mortalidade / 1.000 hab.** | **`7,85`** | **`7,81`** | **`4,10`** (*Itaitinga*) | **`15,03`** (*São João do Jaguaribe*) | **7,35 óbitos / 1.000 hab.** |
| **IDEB Anos Iniciais (2023)** | `6,77` | `6,50` | **`4,90`** (*Ibaretama*) | **`10,00`** (*Pires Ferreira*) | — |
| **IDEB Anos Finais (2023)** | `5,55` | `5,40` | **`4,10`** (*Potengi*) | **`9,20`** (*Pires Ferreira*) | — |
| **Água via Rede Geral (%)** | `71,17%` | `72,65%` | **`26,37%`** (*Aquiraz*) | **`96,95%`** (*Maracanaú*) | — |
| **Esgoto ou Fossa Ligada à Rede (%)** | `21,51%` | `18,42%` | **`0,33%`** (*Chaval*) | **`74,70%`** (*Sobral*) | — |

---

### 3.2. Comparação: Quantidade de Atendimentos vs. Mortalidade vs. IDH vs. Pobreza

Para responder com rigor estatístico se **"onde há mais atendimentos ocorrem mais mortes"** e como os atendimentos se relacionam com **IDH** e **Pobreza**, calculamos o **Coeficiente de Correlação de Pearson ($r$)** sob duas óticas: **Volume Bruto (`TOTAL_ATENDIMENTOS`)** e **Volume Proporcional (`ATENDIMENTOS_POR_100K_HAB`)**.

| Cruzamento Analisado | Correlação ($r$) | Direção e Força | Interpretação Epidemiológica e Socioeconômica |
| :--- | :---: | :---: | :--- |
| **Atendimentos Absolutos vs. População 2022** | **`+0,6497`** | Positiva Forte | Municípios mais populosos geram naturalmente maior volume bruto de atendimentos. |
| **Atendimentos Absolutos vs. Óbitos Totais (2022)** | **`+0,6383`** | Positiva Forte *(Espúria por População)* | Ocorre apenas porque cidades grandes (como Fortaleza e Juazeiro do Norte) têm mais habitantes, tendo simultaneamente mais atendimentos brutos e mais óbitos brutos. |
| **Atendimentos / 100k hab vs. Taxa de Mortalidade / 1k hab** | **`+0,0015`** | **Nula / Inexistente ($\approx 0$)** | **Conclusão Crítica:** Quando corrigimos pelo tamanho da população, **NÃO existe correlação entre ter mais atendimentos e ter mais mortes**. |
| **Atendimentos Absolutos vs. Taxa de Mortalidade / 1k hab** | **`-0,2792`** | Negativa Fraca/Moderada | Municípios com maior volume absoluto de atendimentos tendem inclusive a apresentar taxas brutas de mortalidade ligeiramente menores. |
| **Atendimentos / 100k hab vs. IDH Municipal (2010)** | **`-0,3920`** | **Negativa Moderada** | **Insight Chave:** Quanto **menor o IDH** do município, **maior é a proporção de atendimentos do SUS por 100 mil hab.** Populações de municípios menos desenvolvidos dependem muito mais fortemente da cobertura pública do SUS. |
| **Atendimentos Absolutos vs. IDH Municipal (2010)** | **`+0,4315`** | Positiva Moderada | Grandes polos urbanos (Fortaleza, Sobral, Juazeiro, Maracanaú) têm IDH acima da média estadual (`0,617`) e grande volume absoluto de atendimentos devido à concentração populacional. |
| **Atendimentos / 100k hab vs. Incidência de Pobreza (%)** | **`+0,2301`** | **Positiva** | Municípios com **maior incidência de pobreza** demandam **maior volume proporcional de atendimentos por 100 mil habitantes**, evidenciando o papel redistributivo e equitativo do SUS. |
| **Atendimentos / 100k hab vs. Água via Rede Geral (%)** | **`-0,2499`** | **Negativa** | Municípios com menor cobertura de água encanada apresentam maior demanda proporcional por atendimentos no SUS. |
| **IDH Municipal (2010) vs. Incidência de Pobreza (%)** | **`-0,5156`** | Negativa Forte | Confirma a consistência estrutural das bases do IBGE: municípios com menor IDH possuem taxas de pobreza significativamente mais altas. |

> **Síntese da Descoberta:**
> 1. **Atendimentos vs. Mortalidade:** Onde há mais atendimentos proporcionalmente **não** ocorrem mais mortes ($r = +0,0015$). Os atendimentos refletem acesso à Atenção Primária e prevenção, não letalidade.
> 2. **Atendimentos vs. IDH e Pobreza:** Existe uma relação inversa clara com o IDH ($r = -0,3920$) e direta com a Pobreza ($r = +0,2301$). Municípios mais pobres e de menor IDH têm taxas de atendimento por 100 mil habitantes até **20 vezes maiores** que a capital Fortaleza, demonstrando a capilaridade do SUS no interior vulnerável.

---

### 3.3. Tabelas de Maiores e Menores Valores em VOLUME ABSOLUTO de Atendimentos (e Comparação com o IDH Médio do Ceará = `0,617`)

#### A) 🔼 Top 15 Municípios com MAIOR Volume Absoluto de Atendimentos (`ID`s)
| Pos. | Município | Macrorregião SUS | Volume de Atendimentos | População (2022) | Atend. / 100k hab | IDH (2010) | Comparação com IDH Médio CE (`0,617`) | Pobreza (%) | Óbitos (2022) | Taxa Mort. (/1k hab) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **Fortaleza** | Fortaleza | **9.364** | 2.428.708 | 385,55 | **0,754** | Acima (`+0,137`) | 43,17% | 17.826 | 7,34 |
| **2º** | **Itapipoca** | Fortaleza | **7.620** | 131.123 | 5.811,34 | **0,640** | Acima (`+0,023`) | 57,01% | 794 | 6,06 |
| **3º** | **Juazeiro do Norte** | Cariri | **4.495** | 286.120 | 1.571,02 | **0,694** | Acima (`+0,077`) | 52,14% | 2.062 | 7,21 |
| **4º** | **Maracanaú** | Fortaleza | **4.403** | 234.509 | 1.877,54 | **0,686** | Acima (`+0,069`) | 55,53% | 1.516 | 6,46 |
| **5º** | **Trairi** | Fortaleza | **4.377** | 58.415 | 7.492,94 | **0,606** | Abaixo (`-0,011`) | 58,71% | 389 | 6,66 |
| **6º** | **Quixadá** | Sertão Central | **4.018** | 84.168 | 4.773,79 | **0,659** | Acima (`+0,042`) | 52,84% | 546 | 6,49 |
| **7º** | **Tianguá** | Sobral | **3.926** | 81.506 | 4.816,82 | **0,657** | Acima (`+0,040`) | 52,98% | 527 | 6,47 |
| **8º** | **Sobral** | Sobral | **3.789** | 203.023 | 1.866,29 | **0,714** | Acima (`+0,097`) | 49,30% | 1.382 | 6,81 |
| **9º** | **Maranguape** | Fortaleza | **3.728** | 105.093 | 3.547,33 | **0,659** | Acima (`+0,042`) | 58,54% | 678 | 6,45 |
| **10º** | **Itarema** | Sobral | **3.080** | 42.957 | 7.169,96 | **0,606** | Abaixo (`-0,011`) | 67,99% | 270 | 6,29 |
| **11º** | **Caucaia** | Fortaleza | **2.930** | 355.679 | 823,78 | **0,682** | Acima (`+0,065`) | 52,83% | 2.224 | 6,25 |
| **12º** | **Viçosa do Ceará** | Sobral | **2.899** | 59.712 | 4.854,97 | **0,571** | Abaixo (`-0,046`) | 61,86% | 383 | 6,41 |
| **13º** | **Quixeramobim** | Sertão Central | **2.621** | 82.177 | 3.189,46 | **0,642** | Acima (`+0,025`) | 63,50% | 607 | 7,39 |
| **14º** | **Mauriti** | Cariri | **2.587** | 45.561 | 5.678,10 | **0,605** | Abaixo (`-0,012`) | 62,18% | 319 | 7,00 |
| **15º** | **Granja** | Sobral | **2.518** | 53.344 | 4.720,31 | **0,559** | Abaixo (`-0,058`) | 67,72% | 321 | 6,02 |

#### B) 🔽 Top 15 Municípios com MENOR Volume Absoluto de Atendimentos (`ID`s)
| Pos. | Município | Macrorregião SUS | Volume de Atendimentos | População (2022) | Atend. / 100k hab | IDH (2010) | Comparação com IDH Médio CE (`0,617`) | Pobreza (%) | Óbitos (2022) | Taxa Mort. (/1k hab) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **Ereré** | Litoral Leste/Jaguaribe | **39** | 6.474 | 602,41 | **0,610** | Abaixo (`-0,007`) | 72,24% | 46 | 7,11 |
| **2º** | **Dep. Irapuan Pinheiro** | Sertão Central | **88** | 8.932 | 985,22 | **0,609** | Abaixo (`-0,008`) | 59,08% | 82 | 9,18 |
| **3º** | **Granjeiro** | Cariri | **96** | 4.841 | 1.983,06 | **0,585** | Abaixo (`-0,032`) | 67,22% | 38 | 7,85 |
| **4º** | **São João do Jaguaribe** | Litoral Leste/Jaguaribe | **111** | 5.855 | 1.895,82 | **0,654** | Acima (`+0,037`) | 35,02% | 88 | 15,03 |
| **5º** | **Itaiçaba** | Litoral Leste/Jaguaribe | **114** | 7.536 | 1.512,74 | **0,656** | Acima (`+0,039`) | 52,06% | 63 | 8,36 |
| **6º** | **Guaramiranga** | Fortaleza | **134** | 5.654 | 2.370,00 | **0,637** | Acima (`+0,020`) | 53,42% | 57 | 10,08 |
| **7º** | **Baixio** | Cariri | **146** | 5.704 | 2.559,61 | **0,627** | Acima (`+0,010`) | 54,51% | 54 | 9,47 |
| **8º** | **Arneiroz** | Sertão Central | **163** | 7.429 | 2.194,10 | **0,618** | Acima (`+0,001`) | 65,47% | 59 | 7,94 |
| **9º** | **Groaíras** | Sobral | **168** | 10.910 | 1.539,87 | **0,633** | Acima (`+0,016`) | 59,07% | 109 | 9,99 |
| **10º** | **Antonina do Norte** | Cariri | **192** | 7.245 | 2.650,10 | **0,599** | Abaixo (`-0,018`) | 76,94% | 63 | 8,70 |
| **11º** | **Altaneira** | Cariri | **205** | 6.782 | 3.022,71 | **0,602** | Abaixo (`-0,015`) | 73,46% | 65 | 9,58 |
| **12º** | **Ararendá** | Sobral | **206** | 11.096 | 1.856,52 | **0,590** | Abaixo (`-0,027`) | 66,79% | 104 | 9,37 |
| **13º** | **Alcântaras** | Sobral | **211** | 11.369 | 1.855,92 | **0,600** | Abaixo (`-0,017`) | 49,48% | 74 | 6,51 |
| **14º** | **Frecheirinha** | Sobral | **212** | 15.657 | 1.354,03 | **0,604** | Abaixo (`-0,013`) | 60,89% | 117 | 7,47 |
| **15º** | **Apuiarés** | Fortaleza | **219** | 12.928 | 1.694,00 | **0,618** | Acima (`+0,001`) | 59,25% | 115 | 8,90 |

---

### 3.4. Tabelas de Maiores e Menores Valores em VOLUME PROPORCIONAL de Atendimento (por 100 mil hab.)

#### A) 🔼 Top 15 Municípios com MAIOR Proporção de Atendimentos por 100 mil Habitantes
| Rank | Município | Macrorregião | Atend. / 100k hab | % Pop. Atendida | Atendimentos | População (2022) | IDH (2010) vs. CE (`0,617`) | Pobreza (%) | Taxa Mort. (/1k) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **Penaforte** | Cariri | **8.392,78** | 8,39% | 753 | 8.972 | `0,646` (Acima) | 53,45% | 9,25 |
| **2º** | **Tejuçuoca** | Fortaleza | **7.829,08** | 7,83% | 1.343 | 17.154 | `0,584` (Abaixo) | 68,89% | 5,83 |
| **3º** | **Itatira** | Sertão Central | **7.789,86** | 7,79% | 1.591 | 20.424 | `0,562` (Abaixo) | 73,14% | 7,20 |
| **4º** | **Salitre** | Cariri | **7.695,55** | 7,70% | 1.280 | 16.633 | `0,540` (**Menor do CE**) | 71,17% | 7,03 |
| **5º** | **Uruburetama** | Fortaleza | **7.548,67** | 7,55% | 1.524 | 20.189 | `0,639` (Acima) | 63,03% | 7,43 |
| **6º** | **Trairi** | Fortaleza | **7.492,94** | 7,49% | 4.377 | 58.415 | `0,606` (Abaixo) | 58,71% | 6,66 |
| **7º** | **Santana do Cariri** | Cariri | **7.278,52** | 7,28% | 1.234 | 16.954 | `0,612` (Abaixo) | 71,78% | 7,49 |
| **8º** | **Itarema** | Sobral | **7.169,96** | 7,17% | 3.080 | 42.957 | `0,606` (Abaixo) | 67,99% | 6,29 |
| **9º** | **Orós** | Cariri | **6.622,62** | 6,62% | 1.303 | 19.675 | `0,636` (Acima) | 62,10% | 11,69 |
| **10º** | **Itapiúna** | Fortaleza | **6.602,77** | 6,60% | 1.178 | 17.841 | `0,604` (Abaixo) | 67,03% | 7,23 |
| **11º** | **Tururu** | Fortaleza | **6.540,36** | 6,54% | 1.008 | 15.412 | `0,606` (Abaixo) | 65,25% | 8,69 |
| **12º** | **Martinópole** | Sobral | **6.481,65** | 6,48% | 703 | 10.846 | `0,599` (Abaixo) | 66,57% | 6,64 |
| **13º** | **Monsenhor Tabosa** | Sobral | **6.449,36** | 6,45% | 1.106 | 17.149 | `0,610` (Abaixo) | 60,19% | 9,04 |
| **14º** | **Mulungu** | Fortaleza | **6.433,91** | 6,43% | 680 | 10.569 | `0,607` (Abaixo) | 51,09% | 8,33 |
| **15º** | **Santana do Acaraú** | Sobral | **6.383,05** | 6,38% | 1.955 | 30.628 | `0,587` (Abaixo) | 57,37% | 6,63 |

#### B) 🔽 Top 15 Municípios com MENOR Proporção de Atendimentos por 100 mil Habitantes
| Rank | Município | Macrorregião | Atend. / 100k hab | % Pop. Atendida | Atendimentos | População (2022) | IDH (2010) vs. CE (`0,617`) | Pobreza (%) | Taxa Mort. (/1k) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **Fortaleza** | Fortaleza | **385,55** | 0,39% | 9.364 | 2.428.708 | `0,754` (**Maior do CE**) | 43,17% | 7,34 |
| **2º** | **Ereré** | Litoral Leste/Jaguaribe | **602,41** | 0,60% | 39 | 6.474 | `0,610` (Abaixo) | 72,24% | 7,11 |
| **3º** | **Eusébio** | Fortaleza | **690,31** | 0,69% | 512 | 74.170 | `0,701` (Acima) | 75,48% | 4,73 |
| **4º** | **Caucaia** | Fortaleza | **823,78** | 0,82% | 2.930 | 355.679 | `0,682` (Acima) | 52,83% | 6,25 |
| **5º** | **Horizonte** | Fortaleza | **836,06** | 0,84% | 625 | 74.755 | `0,658` (Acima) | 67,69% | 5,95 |
| **6º** | **Itaitinga** | Fortaleza | **844,55** | 0,84% | 546 | 64.650 | `0,626` (Acima) | 64,12% | 4,10 |
| **7º** | **Dep. Irapuan Pinheiro** | Sertão Central | **985,22** | 0,99% | 88 | 8.932 | `0,609` (Abaixo) | 59,08% | 9,18 |
| **8º** | **Aracati** | Litoral Leste/Jaguaribe | **1.027,78** | 1,03% | 772 | 75.113 | `0,655` (Acima) | 48,81% | 6,79 |
| **9º** | **Iguatu** | Cariri | **1.236,95** | 1,24% | 1.213 | 98.064 | `0,677` (Acima) | 51,19% | 8,45 |
| **10º** | **Barbalha** | Cariri | **1.288,77** | 1,29% | 967 | 75.033 | `0,683` (Acima) | 52,51% | 7,09 |
| **11º** | **Caririaçu** | Cariri | **1.310,79** | 1,31% | 345 | 26.320 | `0,578` (Abaixo) | 62,88% | 7,75 |
| **12º** | **Frecheirinha** | Sobral | **1.354,03** | 1,35% | 212 | 15.657 | `0,604` (Abaixo) | 60,89% | 7,47 |
| **13º** | **Itaiçaba** | Litoral Leste/Jaguaribe | **1.512,74** | 1,51% | 114 | 7.536 | `0,656` (Acima) | 52,06% | 8,36 |
| **14º** | **Groaíras** | Sobral | **1.539,87** | 1,54% | 168 | 10.910 | `0,633` (Acima) | 59,07% | 9,99 |
| **15º** | **Juazeiro do Norte** | Cariri | **1.571,02** | 1,57% | 4.495 | 286.120 | `0,694` (Acima) | 52,14% | 7,21 |

---

### 3.5. Tabelas de Maiores e Menores Valores do Estado em IDH, Pobreza e Mortalidade (Cruzados com os Atendimentos SUS)

#### A) Extremos de IDH Municipal (2010) — Top 10 Maiores vs. Top 10 Menores do Ceará
| Pos. | 🔼 MAIORES IDHs do Ceará | IDH (2010) | Atend. SUS | Atend. / 100k hab | Pobreza (%) | 🔽 MENORES IDHs do Ceará | IDH (2010) | Atend. SUS | Atend. / 100k hab | Pobreza (%) |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **1º** | **Fortaleza** | **0,754** | 9.364 | 385,55 | 43,17% | **Salitre** | **0,540** | 1.280 | **7.695,55** | 71,17% |
| **2º** | **Sobral** | **0,714** | 3.789 | 1.866,29 | 49,30% | **Granja** | **0,559** | 2.518 | **4.720,31** | 67,72% |
| **3º** | **Crato** | **0,713** | 2.266 | 1.729,11 | 44,30% | **Itatira** | **0,562** | 1.591 | **7.789,86** | 73,14% |
| **4º** | **Eusébio** | **0,701** | 512 | 690,31 | 75,48% | **Potengi** | **0,562** | 446 | **5.049,25** | 64,82% |
| **5º** | **Juazeiro do Norte** | **0,694** | 4.495 | 1.571,02 | 52,14% | **Araripe** | **0,564** | 895 | **4.524,09** | 74,30% |
| **6º** | **Maracanaú** | **0,686** | 4.403 | 1.877,54 | 55,53% | **Uruoca** | **0,566** | 735 | **5.347,01** | 64,04% |
| **7º** | **Barbalha** | **0,683** | 967 | 1.288,77 | 52,51% | **General Sampaio** | **0,568** | 242 | 3.593,70 | 63,27% |
| **8º** | **Caucaia** | **0,682** | 2.930 | 823,78 | 52,83% | **Aiuaba** | **0,569** | 570 | **4.049,45** | 66,83% |
| **9º** | **Limoeiro do Norte** | **0,682** | 1.719 | 2.886,17 | 39,92% | **Graça** | **0,570** | 259 | 1.876,68 | 68,84% |
| **10º** | **Iguatu** | **0,677** | 1.213 | 1.236,95 | 51,19% | **Parambu** | **0,570** | 900 | 2.862,14 | 61,90% |

> **Leitura Direta da Tabela:** Nos **10 maiores IDHs do Ceará**, todos os 10 municípios têm taxa de atendimento abaixo da média municipal estadual (`3.624,82 / 100k hab`). Já nos **10 menores IDHs do Ceará**, **7 dos 10 municípios** superam fortemente a média estadual de atendimentos por 100 mil habitantes (chegando a `7.789,86` em Itatira e `7.695,55` em Salitre)!

#### B) Extremos de Incidência de Pobreza (%) — Top 10 Maiores vs. Top 10 Menores do Ceará
| Pos. | 🔼 MAIOR Pobreza no Ceará | Pobreza (%) | Atend. SUS | Atend. / 100k hab | IDH (2010) | 🔽 MENOR Pobreza no Ceará | Pobreza (%) | Atend. SUS | Atend. / 100k hab | IDH (2010) |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **1º** | **Saboeiro** | **79,47%** | 765 | **5.521,87** | 0,575 | **São João do Jaguaribe** | **35,02%** | 111 | 1.895,82 | 0,654 |
| **2º** | **Antonina do Norte** | **76,94%** | 192 | 2.650,10 | 0,599 | **Limoeiro do Norte** | **39,92%** | 1.719 | 2.886,17 | 0,682 |
| **3º** | **Senador Sá** | **76,28%** | 415 | **5.714,68** | 0,603 | **Tabuleiro do Norte** | **40,97%** | 997 | 3.252,64 | 0,645 |
| **4º** | **Eusébio** | **75,48%** | 512 | 690,31 | 0,701 | **Icapuí** | **41,00%** | 503 | 2.346,85 | 0,616 |
| **5º** | **Araripe** | **74,30%** | 895 | **4.524,09** | 0,564 | **Fortaleza** | **43,17%** | 9.364 | 385,55 | 0,754 |
| **6º** | **Altaneira** | **73,46%** | 205 | 3.022,71 | 0,602 | **Crato** | **44,30%** | 2.266 | 1.729,11 | 0,713 |
| **7º** | **Itatira** | **73,14%** | 1.591 | **7.789,86** | 0,562 | **Russas** | **45,21%** | 1.260 | 1.727,73 | 0,674 |
| **8º** | **Miraíma** | **72,72%** | 734 | **5.170,47** | 0,592 | **Quiterianópolis** | **47,37%** | 833 | 4.121,11 | 0,594 |
| **9º** | **Ereré** | **72,24%** | 39 | 602,41 | 0,610 | **Ibiapina** | **48,73%** | 472 | 1.969,54 | 0,608 |
| **10º** | **Poranga** | **72,17%** | 672 | **5.569,83** | 0,581 | **Aracati** | **48,81%** | 772 | 1.027,78 | 0,655 |

#### C) Extremos de Taxa de Mortalidade (por 1.000 hab. em 2022) — Top 10 Maiores vs. Top 10 Menores do Ceará
| Pos. | 🔼 MAIOR Taxa de Mortalidade | Mort. (/1k) | Óbitos (22) | Atend. / 100k hab | IDH (2010) | 🔽 MENOR Taxa de Mortalidade | Mort. (/1k) | Óbitos (22) | Atend. / 100k hab | IDH (2010) |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **1º** | **São João do Jaguaribe** | **15,03** | 88 | 1.895,82 | 0,654 | **Itaitinga** | **4,10** | 265 | 844,55 | 0,626 |
| **2º** | **Orós** | **11,69** | 230 | 6.622,62 | 0,636 | **Eusébio** | **4,73** | 351 | 690,31 | 0,701 |
| **3º** | **Umari** | **10,48** | 72 | 5.908,89 | 0,591 | **Miraíma** | **4,93** | 70 | 5.170,47 | 0,592 |
| **4º** | **Aratuba** | **10,25** | 115 | 3.447,97 | 0,622 | **Jijoca de Jericoacoara** | **5,13** | 131 | 2.919,19 | 0,652 |
| **5º** | **Jaguaribara** | **10,24** | 106 | 4.258,40 | 0,618 | **Pacatuba** | **5,46** | 445 | 2.038,66 | 0,675 |
| **6º** | **Tamboril** | **10,24** | 254 | 5.629,66 | 0,580 | **Morrinhos** | **5,63** | 128 | 4.535,67 | 0,588 |
| **7º** | **Potiretama** | **10,21** | 61 | 4.168,06 | 0,604 | **Tejuçuoca** | **5,83** | 100 | **7.829,08** | 0,584 |
| **8º** | **Guaramiranga** | **10,08** | 57 | 2.370,00 | 0,637 | **Uruoca** | **5,89** | 81 | 5.347,01 | 0,566 |
| **9º** | **Groaíras** | **9,99** | 109 | 1.539,87 | 0,633 | **Horizonte** | **5,95** | 445 | 836,06 | 0,658 |
| **10º** | **Acopiara** | **9,83** | 442 | 2.960,28 | 0,595 | **Granja** | **6,02** | 321 | 4.720,31 | 0,559 |

---

### 3.6. Volume e Proporção de Atendimentos por Região (Macrorregião SUS e Mesorregião IBGE)

#### A) Por Macrorregião de Saúde do SUS Ceará
| Macrorregião de Saúde (SUS) | Nº Municípios | Volume de Atendimentos | % dos Atendimentos | População (2022) | Atendimentos / 100k hab | IDH Médio (2010) | Pobreza Média (%) | Óbitos (2022) | Taxa Mort. (/1k hab) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fortaleza** | 43 | **65.918** | 32,2% | 4.500.359 | `1.464,73` | 0,631 | 60,08% | 31.511 | 7,00 |
| **Sobral** | 54 | **56.594** | 27,7% | 1.623.797 | `3.485,29` | 0,607 | 60,79% | 12.014 | 7,40 |
| **Cariri** | 40 | **39.126** | 19,1% | 1.329.241 | `2.943,48` | 0,616 | 60,96% | 10.555 | 7,94 |
| **Sertão Central** | 25 | **26.851** | 13,1% | 745.908 | **`3.599,77`** | **0,603** | **62,59%** | 5.913 | 7,93 |
| **Litoral Leste/Jaguaribe** | 22 | **16.090** | 7,9% | 595.652 | `2.701,24` | 0,630 | 54,76% | 4.668 | 7,84 |

#### B) Por Mesorregião do IBGE
| Mesorregião (IBGE) | Nº Municípios | Volume de Atendimentos | % dos Atendimentos | População (2022) | Atendimentos / 100k hab | IDH Médio (2010) | Pobreza Média (%) | Óbitos (2022) | Taxa Mort. (/1k hab) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Noroeste Cearense** | 45 | **48.364** | 23,6% | 1.376.589 | `3.513,32` | 0,607 | 60,97% | 9.790 | 7,11 |
| **Norte Cearense** | 35 | **42.716** | 20,9% | 1.046.125 | **`4.083,26`** | 0,614 | 61,08% | 7.587 | 7,25 |
| **Metropolitana de Fortaleza** | 14 | **29.993** | 14,7% | 3.652.622 | `821,14` | **0,657** | 60,11% | 25.362 | 6,94 |
| **Sertões Cearenses** | 27 | **28.132** | 13,8% | 792.637 | `3.549,17` | 0,607 | 60,54% | 6.560 | 8,28 |
| **Sul Cearense** | 26 | **27.691** | 13,5% | 954.126 | `2.902,24` | 0,618 | 60,26% | 7.330 | 7,68 |
| **Jaguaribe** | 21 | **14.645** | 7,2% | 542.538 | `2.699,35` | 0,630 | 54,58% | 4.279 | 7,89 |
| **Centro-Sul Cearense** | 16 | **13.038** | 6,4% | 430.320 | `3.029,84` | 0,612 | 62,72% | 3.753 | 8,72 |

---

### 3.7. Análise Espacial no Mapa Interativo dos Atendimentos SUS

No mapa interativo de bolhas ([`src/wilson/dashboard.py`](file:///home/arthurpcidrao/projetos/wilson/src/wilson/dashboard.py)):
- **Quando o tamanho da bola representa o Volume Absoluto (`TOTAL_ATENDIMENTOS`):** Observam-se grandes esferas concentradas na **Região Metropolitana de Fortaleza** (Fortaleza, Maracanaú, Maranguape, Caucaia), no **Litoral Oeste/Norte** (Itapipoca, Trairi, Itarema), no **Noroeste/Ibiapaba** (Sobral, Tianguá, Viçosa do Ceará), no **Sertão Central** (Quixadá, Quixeramobim) e no **Cariri** (Juazeiro do Norte, Mauriti).
- **Quando o tamanho da bola representa a Proporção por 100 mil hab. (`ATENDIMENTOS_POR_100K_HAB`):** A bolha de Fortaleza diminui drasticamente e emergem dois cinturões de altíssima densidade proporcional de atendimento SUS:
  1. **Cinturão Norte / Vale do Curu e Aracatiaçu:** Itapipoca, Trairi, Uruburetama, Tururu, Tejuçuoca e Itatira.
  2. **Cinturão Extremo Sul / Chapada do Araripe:** Penaforte, Salitre, Santana do Cariri e Mauriti.

---

## 4. Funcionamento dos Filtros e Gráficos no Dashboard Streamlit

### 4.1. Tabela de Parâmetros e Filtros Globais (Barra Lateral / *Sidebar*)

Ao abrir o Dashboard (`uv run streamlit run app.py`), **nenhum filtro vem pré-preenchido com tags poluídas**. O estado natural da aplicação mostra automaticamente **todos os 184 municípios do Ceará**.

| Parâmetro / Controle | Tipo | Como Funciona e Impacto nos Gráficos |
| :--- | :--- | :--- |
| **Apresentar Município(s)** | Seleção Múltipla (`Multiselect`, vazio por padrão) | Por padrão exibe **todos os 184 municípios**. Se você selecionar um município (ex.: `Fortaleza` ou `Penaforte`), o Dashboard filtra todos os KPIs e gráficos para ele, **centraliza o mapa com zoom automático** e abre no topo um **Card de Comparação Direta** contra a Média Estadual do Ceará. |
| **Agrupamento Regional** | Seletor (`Radio`) | Alterna toda a agregação regional do painel entre **Macrorregião de Saúde (SUS)** (*5 macrorregiões*) e **Mesorregião (IBGE)** (*7 mesorregiões*). |
| **Filtrar Região (Opcional)** | Seleção Múltipla (`Multiselect`, vazio por padrão) | Vazio = todas as regiões. Quando preenchido, filtra os municípios pertencentes às regiões selecionadas. |
| **Filtrar Porte Populacional (Opcional)** | Seleção Múltipla (`Multiselect`, vazio por padrão) | Vazio = todos os portes. Permite isolar **Pequeno Porte (`< 20 mil hab`)**, **Médio Porte (`20 a 50 mil hab`)**, **Médio-Grande (`50 a 100 mil hab`)** ou **Grande Porte (`> 100 mil hab`)**. |
| **Municípios nos Rankings (Top / Bottom N)** | Controle Deslizante (`Slider: 5 a 30`) | Define quantos municípios são exibidos simultaneamente nos gráficos de maiores (*Top N*) e menores (*Bottom N*) volumes proporcionais e absolutos. |
| **🔄 Mostrar Todos os 184 Municípios** | Botão Dinâmico (`Button`) | Aparece automaticamente sempre que algum filtro está ativo, permitindo restaurar o estado natural (todos os 184 municípios) com 1 clique. |

---

## 5. Separação dos Slides para Apresentação

Abaixo está a estrutura pronta para os slides da apresentação da equipe:

---

### 🖥️ SLIDE 1: Capa
- **Título:** Enriquecimento de Dados e Inteligência Epidemiológica dos Atendimentos SUS no Ceará
- **Subtítulo:** Integração da Base de Atendimentos (`DADOS.txt`) com Indicadores Demográficos, Socioeconômicos, Educacionais e de Mortalidade do IBGE (184 Municípios)
- **Integrantes da Equipe:**
  - **Arthur**
  - **Braule**
  - **Lucas**
  - **Guilherme**
  - **Eduardo**
- **Ferramentas Utilizadas:** Python, Pandas, Plotly, Streamlit e gerenciador de pacotes **UV**.

---

### 🖥️ SLIDE 2: Como Foi Feito o Enriquecimento dos Dados
- **Base de Referência:** Arquivo [`DADOS.txt`](file:///home/arthurpcidrao/projetos/wilson/DADOS.txt) contendo `204.579` atendimentos individuais com `ID`, `MUNICÍPIO` e `PRIMEIRO_NOME`.
- **Estratégia de Chave de Junção (`MUNICIPIO_CHAVE`):**
  - Como os CSVs originais não possuíam o código numérico do IBGE, construiu-se uma chave textual normalizada (maiúscula, sem espaços laterais e sem acentos via Unicode `NFKD`).
  - Incorporamos o **Código IBGE oficial de 7 dígitos (`CODIGO_IBGE`)**, **Macrorregião de Saúde do SUS**, **Mesorregião IBGE** e coordenadas geográficas (`LATITUDE` e `LONGITUDE`) para os **184 municípios cearenses**.
- **Bases do IBGE Cruzadas (`Left/Inner Join` 100% pareado):**
  1. **Censo Demográfico 2022:** População residente (`8,79 milhões`), área, densidade demográfica e saneamento básico (água, esgoto, lixo, banheiro).
  2. **Mortalidade (2006–2022):** Série histórica de 17 anos de óbitos, mortalidade infantil e causas de óbito por capítulo da CID-10 em 2022.
  3. **Mapa de Pobreza e Desigualdade:** Incidência de pobreza (%), pobreza subjetiva (%) e Índice de Gini.
  4. **IDH Municipal:** Série histórica (1991, 2000 e 2010) e evolução percentual.
  5. **IDEB (2005–2025):** Evolução da educação básica pública (Anos Iniciais e Anos Finais).

---

### 🖥️ SLIDE 3: Limpeza dos Dados e Validação ("Os Dados Fazem Sentido?")
- **Tratamentos e Filtragens Aplicados na Entrada:**
  1. **Remoção de *Padding*:** `100%` das `204.579` linhas de `DADOS.txt` tinham `MUNICÍPIO` preenchido com espaços até 100 caracteres.
  2. **Correção de Divergências Ortográficas Históricas:**
     - `ITAPAGÉ` (`DADOS.txt`) $\rightarrow$ `Itapajé` (IBGE).
     - `ERERÊ` (`DADOS.txt`) $\rightarrow$ `Ereré` (IBGE).
  3. **Higienização de Nomes Corrompidos:** `17` registros corrigidos (`16` com caractere inválido `\ufffd` como `MARIA` $\rightarrow$ `MARIA` e `TILA` $\rightarrow$ `ATILA`, e `1` com dígito em `J0SE` $\rightarrow$ `JOSE`).
  4. **Regra do `ID` Único (Não Agrupamento por Nome):** `204.579` IDs únicos validados (`0` nulos e `0` duplicados). Existem apenas `9.749` primeiros nomes distintos (`MARIA` = `48.242` atendimentos; `FRANCISCA` = `14.179`; `ANTONIA` = `12.346`). Agrupar por nome eliminaria `95,2%` dos atendimentos reais!
- **Validação Demográfica Crítica — *"Há municípios com mais atendimentos que habitantes?"*:**
  - **NÃO (`0 de 184 municípios`).**
  - A maior cobertura proporcional ocorre em **Penaforte**, com `753` atendimentos para `8.972` habitantes (`8,39%` da população). Portanto, os volumes de atendimento são **totalmente plausíveis e compatíveis com o porte populacional** de cada município.

---

### 🖥️ SLIDE 4: Principais Insights Observados (Maiores e Menores Valores do Estado)
- **Tabela Resumo dos Extremos do Ceará (184 Municípios):**

| Indicador | Média Estadual (CE) | 🔽 MENOR Valor no Ceará | 🔼 MAIOR Valor no Ceará |
| :--- | :---: | :--- | :--- |
| **Atendimentos SUS (Absoluto)** | `1.111,84` | **`39`** (*Ereré*) | **`9.364`** (*Fortaleza*) |
| **Atendimentos / 100 mil hab.** | `3.624,82` | **`385,55`** (*Fortaleza*) | **`8.392,78`** (*Penaforte*) |
| **População Residente (2022)** | `47.798,68` | **`4.841`** (*Granjeiro*) | **`2.428.708`** (*Fortaleza*) |
| **IDH Municipal (2010)** | `0,617` | **`0,540`** (*Salitre*) | **`0,754`** (*Fortaleza*) |
| **Incidência de Pobreza (%)** | `60,18%` | **`35,02%`** (*São João do Jaguaribe*) | **`79,47%`** (*Saboeiro*) |
| **Taxa de Mortalidade (/1k hab)** | `7,85` | **`4,10`** (*Itaitinga*) | **`15,03`** (*São João do Jaguaribe*) |

- **Top 5 Maior vs. Menor Volume Absoluto e Proporcional:**
  - **Maior Volume Absoluto:** 1º Fortaleza (`9.364`, IDH `0,754`), 2º Itapipoca (`7.620`, IDH `0,640`), 3º Juazeiro do Norte (`4.495`, IDH `0,694`), 4º Maracanaú (`4.403`, IDH `0,686`), 5º Trairi (`4.377`, IDH `0,606`).
  - **Menor Volume Absoluto:** 1º Ereré (`39`, IDH `0,610`), 2º Dep. Irapuan Pinheiro (`88`, IDH `0,609`), 3º Granjeiro (`96`, IDH `0,585`), 4º São João do Jaguaribe (`111`, IDH `0,654`), 5º Itaiçaba (`114`, IDH `0,656`).
  - **Maior Proporção (/100k hab):** 1º Penaforte (`8.392,78`), 2º Tejuçuoca (`7.829,08`), 3º Itatira (`7.789,86`), 4º Salitre (`7.695,55`, menor IDH do CE `0,540`), 5º Uruburetama (`7.548,67`).
  - **Menor Proporção (/100k hab):** 1º Fortaleza (`385,55`, maior IDH do CE `0,754`), 2º Ereré (`602,41`), 3º Eusébio (`690,31`, IDH `0,701`), 4º Caucaia (`823,78`, IDH `0,682`), 5º Horizonte (`836,06`, IDH `0,658`).
- **Cruzamento Estatístico (Mortalidade, IDH e Pobreza):**
  - **Atendimentos/100k vs. Taxa de Mortalidade/1k hab ($r = +0,0015$):** **Não há correlação.** Mais atendimentos no SUS significam maior cobertura preventiva/ambulatorial, e não maior mortalidade.
  - **Atendimentos/100k vs. IDH ($r = -0,3920$) e Pobreza ($r = +0,2301$):** Municípios com **menor IDH** e **maior pobreza** apresentam taxas de atendimento SUS por 100 mil habitantes muito superiores à média estadual.

---

### 🖥️ SLIDE 5: Breve Relatório do Enriquecimento e Justificativa das Análises
- **Resumo Executivo do Enriquecimento:**
  - Transformamos uma tabela simples de 3 colunas (`ID`, `MUNICÍPIO`, `PRIMEIRO_NOME`) em um *Data Mart* multidimensional de saúde pública com **56 variáveis** por município, cobrindo demografia, saneamento, pobreza, desigualdade, educação e 17 anos de mortalidade.
- **Justificativa Metodológica das Análises Escolhidas:**
  - **Por que usar a taxa por 100 mil habitantes?** Porque comparar o volume bruto de Fortaleza (`2,42 milhões` de hab.) com Penaforte (`8,9 mil` hab.) distorce a análise de cobertura. A normalização por `100.000` habitantes revela a real penetração do serviço público na população local.
  - **Por que cruzar com Pobreza, IDH e Saneamento?** A saúde pública é determinada por fatores socioeconômicos (*Determinantes Sociais da Saúde*). O cruzamento provou estatisticamente que o SUS atua com maior intensidade proporcional justamente nos municípios mais pobres e de menor IDH.
  - **Por que cruzar com Mortalidade (2006–2022 e CID-10)?** Para separar **demanda assistencial** de **desfecho fatal**, demonstrando que a alta procura por atendimentos não decorre de excesso de óbitos, além de mapear que as principais causas de morte no estado são doenças do aparelho circulatório, neoplasmas e causas externas.

---

### 🖥️ SLIDE 6: Confirmação da Coesão dos Dados
- **O que é Coesão dos Dados?**
  - Na ciência de dados, estatística e governança da informação, a **coesão** verifica se um conjunto de informações de múltiplas fontes é **consistente, lógico e harmonioso entre si**, sem contradições internas ou externas.
- **Veredito da Equipe: ✅ COESÃO DOS DADOS CONFIRMADA!**
- **Evidências Objetivas que Comprovam a Coesão:**
  1. **Consistência Geográfica e Referencial (100%):** Todos os `184` municípios presentes em `DADOS.txt` correspondem exatamente aos `184` municípios oficiais do Ceará nas 5 bases do IBGE (após padronização ortográfica de `Itapajé` e `Ereré`).
  2. **Consistência Demográfica (100%):** Nenhum município apresentou volume de atendimentos superior à população residente do Censo 2022 (`0` contradições demográficas; faixa de cobertura entre `0,39%` e `8,39%` da população).
  3. **Consistência Primária e Transacional (100%):** Os `204.579` atendimentos possuem `ID`s íntegros, sem duplicidade e sem valores nulos, com distribuição de homônimos compatível com a demografia brasileira (`MARIA`, `FRANCISCA`, `ANTONIA`, `ANA`).
  4. **Harmonia Estatística e Socioeconômica:** As correlações entre as bases independentes são teoricamente coerentes — o IDH correlaciona-se negativamente com a Pobreza ($r = -0,5156$), positivamente com o acesso à água tratada, e a cobertura proporcional do SUS concentra-se nos municípios de menor IDH ($r = -0,3920$) e maior pobreza ($r = +0,2301$), confirmando que os dados fazem total sentido juntos para tomada de decisão em saúde pública.
