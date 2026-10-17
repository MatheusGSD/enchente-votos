# Enchente de 2024 e voto para presidente na Grande Porto Alegre

A enchente de maio de 2024 mudou o voto para presidente de quem vota nas áreas alagadas? Este repositório cruza o
1º turno de 2018, 2022 e 2026, local de votação por local de votação, com a mancha da enchente em 42 municípios da
Grande Porto Alegre.

**Mapa interativo:** https://matheusgsd.github.io/enchente-votos/

## O que os números mostram

- **O voto andou igual dentro e fora da água.** De 2022 para 2026, a diferença PT − PL caiu 8,6 pontos nos locais
  alagados e 7,9 no restante. A diferença entre os dois (−0,8 ponto, intervalo de 95% de −2,4 a +1,5) é menor que
  a margem de acaso.
- **O eleitorado das áreas alagadas encolheu mais.** Os eleitores aptos caíram 4,7% nas seções dos locais alagados
  e 2,9% no restante. Essa é a única diferença que sai da margem de acaso. Antes da enchente (2018 → 2022), os dois
  grupos cresciam no mesmo ritmo.

É uma comparação descritiva: mostra onde o voto foi diferente, não mede o efeito da enchente.

## Como foi feito

Cada seção eleitoral é a mesma nas três eleições (mesmo município, zona e número) e é posta no local onde votou em
2026. Um local é "alagado" quando o ponto dele cai dentro da mancha. A margem de acaso vem de 2.000 sorteios das
57 zonas eleitorais. Os detalhes estão no cabeçalho de cada script.

| Script | O que faz |
| --- | --- |
| `01_votos.py` | Votos por seção e por local, a partir dos arquivos do TSE |
| `02_analise.py` | Locais dentro e fora da mancha, com critérios alternativos |
| `03_mapas.py` · `04_galeria.py` | Mapas do voto em 2026 e a galeria `saida/galeria.html` |
| `05_mudanca.py` · `06_mapas_mudanca.py` | Mudança de 2022 para 2026 nas mesmas seções |
| `07_infograficos.py` · `08_so_alagados.py` | Cartões para redes sociais e mapas só dos alagados |
| `09_apresentacao.py` | Apresentação em PowerPoint |
| `10_tendencia_2018.py` | 2018, 2022 e 2026 nas mesmas seções: a checagem de antes da enchente |
| `11_incerteza.py` | Intervalo de 95% por reamostragem das zonas eleitorais |
| `12_figuras_artigo.py` | Figuras limpas para o artigo (`saida/artigo/`) |
| `13_exportar_web.py` | Dados do mapa interativo (`docs/dados/`) |

Para rodar do zero, baixe os dados brutos para `dados/` (fora do git, cerca de 1,4 GB) e rode os scripts em ordem.
Precisa de Python com geopandas, matplotlib e shapely 2.1 ou mais novo.

## Fontes

- TSE, [dados abertos](https://dadosabertos.tse.jus.br/): votação por seção e locais de votação, 1º turno de 2018,
  2022 e 2026.
- UFRGS/IPH, Possantti et al., Banco de dados das cheias da RH do Guaíba v1.4: área diretamente afetada em 6 e
  8/5/2024 e simulação do Guaíba a 5,30 m em Porto Alegre (CC BY 4.0). No mapa interativo, o contorno foi
  simplificado.
- IBGE: malha municipal 2025 e setores do Censo 2022. SEMA-RS: base cartográfica 1:25.000.

## Licença

Código sob a licença MIT (`LICENSE`). Figuras, mapas e dados derivados em `saida/` e `docs/` sob
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt-br): pode reusar, citando Matheus Dalmolin e as
fontes acima.
