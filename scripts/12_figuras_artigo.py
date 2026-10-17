"""Figuras para o artigo (Substack): só o gráfico e a legenda mínima, sem título, numeração nem rodapé de fontes.

Título, legenda e fontes vão no texto do artigo, na legenda da imagem. Largura de 1456 px, a que o Substack
recomenda para a coluna do texto (exibida a 728 px); as letras são maiores que nos cartões por isso.
Reaproveita os desenhos de 03_mapas.py, 06_mapas_mudanca.py e 07_infograficos.py.
Saída: saida/artigo/fig*.png
"""
import importlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
MM = importlib.import_module("06_mapas_mudanca")
INF = importlib.import_module("07_infograficos")
COR, SAIDA, DPI = M.COR, M.SAIDA, M.DPI

ART = SAIDA / "artigo"
ART.mkdir(parents=True, exist_ok=True)
W = 1456 / DPI  # polegadas
FS = 16


def figura(h):
    return plt.figure(figsize=(W, h), dpi=DPI, facecolor=COR["fundo"])


def salvar(fig, nome):
    out = ART / nome
    fig.savefig(out, dpi=DPI, facecolor=COR["fundo"])
    plt.close(fig)
    return out


def mapa_com_legenda(L, desenhar, legenda, h_leg=1.5):
    """Mapa na largura toda e a faixa de legenda embaixo; a altura sai da proporção da moldura."""
    frame = L["moldura"].total_bounds
    h_mapa = W * 0.96 / M.proporcao(frame)
    H = h_mapa + h_leg
    fig = figura(H)
    ax = fig.add_axes([0.02, h_leg / H, 0.96, h_mapa / H])
    desenhar(ax, frame)
    legenda(fig, [0.02, 0.15 / H, 0.96, (h_leg - 0.3) / H])
    return fig


def fig1_mapa(L, vmax):
    """Voto em 2026 no entorno de cada local, com a mancha hachurada por cima."""
    def desenhar(ax, frame):
        M.base(ax, L, frame)
        M.voto(ax, L, "areas", 105, vmax)
        M.mancha(ax, L["mancha_ufrgs"], "areas")
        M.rotulos_municipios(ax, fs=11)
        M.rotulo_lago(ax, L, frame, fs=12)

    fig = mapa_com_legenda(L, desenhar, lambda f, r: M.legenda(f, r, "areas", 105, vmax, fs=FS - 2))
    return salvar(fig, "fig1_mapa_voto_2026.png")


def fig2_tres_eleicoes(N18):
    """Diferença PT − PSL/PL nas mesmas seções em 2018, 2022 e 2026, com a tabelinha dos valores embaixo."""
    H = 7.6
    fig = figura(H)
    INF.tres_eleicoes(fig, [0.04, 0.34, 0.86, 0.62], N18, fs=FS - 1)
    return salvar(fig, "fig2_tres_eleicoes.png")


def fig3_aptos(N18):
    """Variação dos eleitores aptos antes e depois da enchente, mesmas seções."""
    H = 4.6
    fig = figura(H)
    INF.legenda_grupos(fig, 0.04, 0.88, FS - 1)
    INF.antes_depois(fig, [0.04, 0.06, 0.92, 0.72], N18, "mudanca_aptos_pct", fs=FS, unidade="%", rot_w=0.26)
    return salvar(fig, "fig3_eleitores_aptos.png")


def fig4_mudanca(L, vmax):
    """Mudança 2022 → 2026 em todos os locais, com a mancha hachurada por cima: a região inteira andou para o PL,
    dentro e fora da água (pintar só os alagados dava a impressão de que só eles mudaram)."""
    def desenhar(ax, frame):
        MM.painel(ax, L, frame, "areas", "mud", 105, vmax, fs_lago=12)
        M.rotulos_municipios(ax, fs=11)

    titulo = "Mudança na diferença PT − PL de 2022 para 2026, em pontos"
    fig = mapa_com_legenda(L, desenhar, lambda f, r: MM.legenda_classes(f, r, MM.CLASSES_MUD, titulo, FS - 2,
                                                                         "areas", mancha_x=0.8))
    return salvar(fig, "fig4_mudanca_2022_2026.png")


def main():
    L, _, _ = MM.carregar()
    N18 = json.loads((SAIDA / "numeros_2018.json").read_text(encoding="utf-8"))
    for velho in ART.glob("fig*.png"):
        velho.unlink()
    print(fig1_mapa(L, float(L["locais"].validos.max())))
    print(fig2_tres_eleicoes(N18))
    print(fig3_aptos(N18))
    print(fig4_mudanca(L, float(L["m_locais"][["validos22", "validos26"]].max().max())))


if __name__ == "__main__":
    main()
