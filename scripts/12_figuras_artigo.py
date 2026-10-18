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
import numpy as np
from matplotlib.collections import LineCollection

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


# figura 2: o mesmo desenho do cartão "Dentro × fora da área alagada" do mapa interativo (docs/app.js). Sem cor de
# partido nem bolinhas nas linhas, para não lembrarem os pontos do mapa; o fundo diz quem venceu
LINHAS = {"dentro": dict(color=COR["texto"], lw=3.4, ls="-", rot="Locais de votação dentro da área alagada"),
          "fora": dict(color="#7d7b74", lw=2.8, ls=(0, (4, 2.3)), rot="Locais de votação fora da área alagada")}
FUNDO_PT, FUNDO_PL = "#fbe9e5", "#e6eef9"
TEXTO_PT, TEXTO_PL = "#d4574a", "#3f74c2"


def fig2_tres_eleicoes(N18):
    """Vantagem do PT sobre o PSL/PL em 2018, 2022 e 2026 nas mesmas seções, dentro e fora da área alagada, com a
    distância entre as duas linhas embaixo de cada ano."""
    g = N18["criterios"]["ada"]
    ys = {k: [g[k][f"margem_{a}"] for a, _, _ in INF.ANOS_18] for k in LINHAS}
    H = 7.8
    fig = figura(H)
    y0, y1, x0, x1 = -36, 8, -0.45, 2.45
    ax = INF.eixo_livre(fig, [0.03, 0.30, 0.86, 0.50], xlim=(x0, 2.75), ylim=(y0, y1))
    fs = FS - 1
    # legenda em cima: uma amostra de cada linha
    for i, (k, s) in enumerate(LINHAS.items()):
        yl = 0.955 - i * 0.055
        fig.add_artist(plt.Line2D([0.03, 0.09], [yl, yl], color=s["color"], lw=s["lw"], ls=s["ls"],
                                  solid_capstyle="round"))
        fig.text(0.105, yl, s["rot"], fontsize=fs, va="center")
    ax.axhspan(0, y1, xmin=0, xmax=(x1 - x0) / (2.75 - x0), color=FUNDO_PT, zorder=0, lw=0)
    ax.axhspan(y0, 0, xmin=0, xmax=(x1 - x0) / (2.75 - x0), color=FUNDO_PL, zorder=0, lw=0)
    for x in range(3):
        ax.plot([x, x], [y0, y1], color="white", lw=1.6, zorder=1)
    ax.plot([x0, x1], [0, 0], color=COR["texto3"], lw=1, zorder=2)
    ax.text(x1 + 0.04, 0, "empate", fontsize=fs - 2, color=COR["texto3"], va="center")
    ax.text(x0 + 0.04, y1 - 1, "PT venceu", fontsize=fs - 1.5, color=TEXTO_PT, weight="bold", va="top")
    ax.text(x1 - 0.04, y0 + 1, "PSL/PL venceu", fontsize=fs - 1.5, color=TEXTO_PL, weight="bold", ha="right",
            va="bottom")
    # a enchente cai entre a eleição de 2022 e a de 2026
    ax.plot([1.6, 1.6], [y0, y1 + 1], color=COR["texto2"], lw=1.2, ls=(0, (1.5, 2.5)), zorder=2, clip_on=False)
    ax.text(1.6, y1 + 1.6, "enchente, maio de 2024", ha="center", va="bottom", fontsize=fs - 2.5, color=COR["texto2"])
    for k in ("fora", "dentro"):
        s = LINHAS[k]
        ax.plot([0, 1, 2], ys[k], color=s["color"], lw=s["lw"], ls=s["ls"], solid_capstyle="round",
                solid_joinstyle="round", zorder=3)
    for x, (_, ano, quem) in enumerate(INF.ANOS_18):
        ax.text(x, y0 - 1.5, ano, ha="center", va="top", fontsize=fs + 1, weight="bold")
        ax.annotate(quem, (x, y0 - 1.5), xytext=(0, -(fs + 8)), textcoords="offset points", ha="center", va="top",
                    fontsize=fs - 2.5, color=COR["texto2"], linespacing=1.1, annotation_clip=False)
        d = ys["dentro"][x] - ys["fora"][x]
        ax.annotate(f"{abs(d):.1f}".replace(".", ","), (x, y0 - 1.5), xytext=(0, -(fs + 8) - 3.4 * (fs - 2.5)),
                    textcoords="offset points", ha="center", va="top", fontsize=fs + 1, weight="bold",
                    annotation_clip=False)
    ax.annotate("distância entre\nas duas linhas,\nem pontos", (x1 + 0.04, y0 - 1.5),
                xytext=(0, -(fs + 8) - 3.4 * (fs - 2.5)), textcoords="offset points", va="top",
                fontsize=fs - 2.5, color=COR["texto2"], linespacing=1.1, annotation_clip=False)
    return salvar(fig, "fig2_tres_eleicoes.png")


# setas de deslocamento: o mesmo código visual do passo "Mudança" do mapa interativo (docs/app.js)
SETA_INCL = np.radians(35)
SETA_TAM = [11, 20, 32]  # px na figura de 1456 px, para até 4, 4 a 10 e mais de 10 pontos
SETA_COR = {"pt": "#d4574a", "pl": "#3f74c2"}
COR_VAZIO = "#a9a59c"


def faixa_seta(v):
    return 0 if abs(v) < 4 else 1 if abs(v) < 10 else 2


def caminho_seta(x, y, d, L_px, px):
    """Haste e as duas pontas da cabeça; d = +1 (para o PL, à direita) ou −1 (para o PT). L_px em pixels da figura,
    px = tamanho de 1 pixel na unidade do eixo (a cabeça segue a mesma regra do mapa interativo)."""
    L, cab = L_px * px, min(9, 3 + 0.3 * L_px) * px
    x2, y2 = x + d * L * np.cos(SETA_INCL), y + L * np.sin(SETA_INCL)
    ang = np.arctan2(y2 - y, x2 - x)
    return [[(x, y), (x2, y2)]] + [[(x2, y2), (x2 - cab * np.cos(ang + a), y2 - cab * np.sin(ang + a))] for a in (-0.5, 0.5)]


def setas(ax, pts, m_por_px):
    """Uma seta por local: os de fora apagados primeiro, os alagados fortes por cima; sem comparação, círculo vazio."""
    for alagado, alfa, lw in [(False, 0.32, 1.4), (True, 1.0, 2.3)]:
        g = pts[pts.ada == alagado]
        vazios = g[~g.comparavel | g.mudanca.isna()]
        ax.scatter(vazios.geometry.x, vazios.geometry.y, s=14, facecolors="none", edgecolors=COR_VAZIO,
                   linewidths=1, alpha=alfa, zorder=7)
        for cor, sinal in [("pl", -1), ("pt", 1)]:
            h = g[g.comparavel & (np.sign(g.mudanca) == sinal)]
            seg = [s for _, r in h.iterrows()
                   for s in caminho_seta(r.geometry.x, r.geometry.y, -sinal, SETA_TAM[faixa_seta(r.mudanca)], m_por_px)]
            ax.add_collection(LineCollection(seg, colors=SETA_COR[cor], linewidths=lw, alpha=alfa, capstyle="round",
                                             zorder=8 if alagado else 7))
    for t in ax.texts:  # nomes de município e do lago por cima das setas, com o contorno claro de 03_mapas
        t.set_zorder(9)


def legenda_setas(fig, rect, fs):
    """Direção, os três tamanhos, alagados × resto e a mancha, numa faixa só (desenhada em pixels da figura)."""
    ax = MM.eixo_livre(fig, rect)
    px = fig.bbox.width * rect[2]  # largura da faixa em px
    u = 1 / px  # 1 px em unidades do eixo (x); no y, a faixa é mais baixa
    ry = fig.bbox.width * rect[2] / (fig.bbox.height * rect[3])

    def seta_leg(x, y, d, L, cor, alfa=1, lw=2):
        seg = caminho_seta(x, y, d, L, u)
        seg = [[(a, y + (b - y) * ry), (c, y + (e - y) * ry)] for (a, b), (c, e) in seg]
        ax.add_collection(LineCollection(seg, colors=cor, linewidths=lw, alpha=alfa, capstyle="round"))

    ax.text(0, 0.95, "Para onde o voto andou de 2022 para 2026 (diferença PT − PL, em pontos)", fontsize=fs,
            color=COR["texto2"], va="top")
    y = 0.4
    seta_leg(0.035, y, -1, 26, SETA_COR["pt"])
    ax.text(0.045, y + 0.08, "para o PT", fontsize=fs - 1.5, va="center")
    seta_leg(0.14, y, 1, 26, SETA_COR["pl"])
    ax.text(0.17, y + 0.08, "para o PL", fontsize=fs - 1.5, va="center")
    x = 0.26
    for L, rot in zip(SETA_TAM, ["até 4", "4 a 10", "mais de 10"]):
        seta_leg(x, y, 1, L, SETA_COR["pl"])
        ax.text(x + L * u * np.cos(SETA_INCL) + 0.008, y + 0.08, rot, fontsize=fs - 1.5, va="center")
        x += 0.085
    seta_leg(0.555, y, 1, 20, SETA_COR["pl"], lw=2.3)
    ax.text(0.58, y + 0.08, "dentro da área alagada", fontsize=fs - 1.5, va="center")
    seta_leg(0.752, y, 1, 20, SETA_COR["pl"], alfa=0.32, lw=1.4)
    ax.text(0.777, y + 0.08, "fora dela", fontsize=fs - 1.5, va="center")
    M.amostra_mancha(ax, 0.845, y - 0.05, 0.035, 0.25, "areas")
    ax.text(0.888, y + 0.08, "Área alagada\nem maio de 2024", fontsize=fs - 1.5, va="center", linespacing=1.2)


def fig3_mudanca(L):
    """Mudança 2022 → 2026 com setas: a região inteira andou para o PL, dentro e fora da água. Com cores de partido,
    a mudança parecia dizer quem ganhou; a seta diz para onde o voto foi."""
    pts = L["m_locais"]

    def desenhar(ax, frame):
        M.base(ax, L, frame)
        M.mancha(ax, L["mancha_ufrgs"], "areas")
        M.rotulos_municipios(ax, fs=11)
        M.rotulo_lago(ax, L, frame, fs=12)
        ax.figure.canvas.draw()  # para medir o tamanho do eixo em px
        m_por_px = (frame[2] - frame[0]) / ax.get_window_extent().width
        setas(ax, pts, m_por_px)

    fig = mapa_com_legenda(L, desenhar, lambda f, r: legenda_setas(f, r, FS - 2))
    return salvar(fig, "fig3_mudanca_2022_2026.png")


def main():
    L, _, _ = MM.carregar()
    N18 = json.loads((SAIDA / "numeros_2018.json").read_text(encoding="utf-8"))
    for velho in ART.glob("fig*.png"):
        velho.unlink()
    print(fig1_mapa(L, float(L["locais"].validos.max())))
    print(fig2_tres_eleicoes(N18))
    print(fig3_mudanca(L))


if __name__ == "__main__":
    main()
