"""Cartão para o X (1600 x 900): mapa das setas de 2022 → 2026 e os números principais.

O mapa é o da figura 3 do artigo (12_figuras_artigo.py), recortado no miolo da região; os números vêm de
docs/dados/resumo.json, os mesmos do cartão "Dentro × fora da área alagada" do mapa interativo.
Uso: python -P scripts/14_imagem_x.py   (depois de 12 e 13)
Saída: saida/imagem_x.png
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
A = importlib.import_module("12_figuras_artigo")
COR, SAIDA, DPI = M.COR, M.SAIDA, M.DPI

W, H = 1600 / DPI, 900 / DPI
MAPA = [0.0, 0.0, 0.53, 1.0]
CENTRO, ALTURA = (478_000, 6_688_000), 66_000  # miolo: Porto Alegre a Novo Hamburgo, em metros (EPSG 31982)
DADOS = "Consolas"
URL = "matheusgsd.github.io/enchente-votos"


def num(v, sinal=True):
    s = f"{v:+.1f}" if sinal else f"{abs(v):.1f}"
    return s.replace(".", ",").replace("-", "−")


def mapa(fig, L):
    ax = fig.add_axes(MAPA)
    h = ALTURA
    w = h * (MAPA[2] * W) / (MAPA[3] * H)
    frame = (CENTRO[0] - w / 2, CENTRO[1] - h / 2, CENTRO[0] + w / 2, CENTRO[1] + h / 2)
    M.base(ax, L, frame)
    M.mancha(ax, L["mancha_ufrgs"], "areas")
    M.rotulos_municipios(ax, fs=10)
    fig.canvas.draw()
    caixa = ax.get_window_extent()
    for txt in ax.texts:  # rótulo cortado pela borda do recorte sai
        e = txt.get_window_extent()
        if e.x0 < caixa.x0 or e.x1 > caixa.x1 or e.y0 < caixa.y0 or e.y1 > caixa.y1:
            txt.remove()
    A.setas(ax, L["m_locais"], (frame[2] - frame[0]) / ax.get_window_extent().width)


def legenda(fig, x, y, fs):
    """Direção da seta, alagados × resto e a mancha, em pixels da figura."""
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, fig.bbox.width)
    ax.set_ylim(0, fig.bbox.height)
    ax.axis("off")
    X, Y = x * fig.bbox.width, y * fig.bbox.height

    def seta(px, cor, d=1, alfa=1, lw=2.2):
        seg = A.caminho_seta(px, Y - 6, d, 22, 1)
        ax.add_collection(LineCollection(seg, colors=cor, linewidths=lw, alpha=alfa, capstyle="round"))

    itens = [(lambda p: seta(p, A.SETA_COR["pt"], -1), "para o PT", 18),
             (lambda p: seta(p, A.SETA_COR["pl"]), "para o PL", 0),
             (lambda p: seta(p, A.SETA_COR["pl"]), "dentro da área alagada", 0),
             (lambda p: seta(p, A.SETA_COR["pl"], alfa=0.32, lw=1.4), "fora dela", 0)]
    px = X
    for i, (desenha, rot, recuo) in enumerate(itens):
        if i == 2:  # segunda linha
            px, Y = X, Y - 34
        desenha(px + recuo)
        t = ax.text(px + 30, Y, rot, fontsize=fs, color=COR["texto2"], va="center")
        fig.canvas.draw()
        px = t.get_window_extent().x1 + 28
    M.amostra_mancha(ax, px, Y - 9, 26, 18, "areas")
    ax.text(px + 34, Y, "área alagada em maio de 2024", fontsize=fs, color=COR["texto2"], va="center")


def main():
    L, _, _ = MM.carregar()
    R = json.loads((M.RAIZ / "docs/dados/resumo.json").read_text(encoding="utf-8"))
    d, f = R["dentro"], R["fora"]
    dist = [abs(a - b) for a, b in zip(R["linhas"]["dentro"], R["linhas"]["fora"])]

    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=COR["fundo"])
    mapa(fig, L)

    x0 = 0.57
    t = lambda y, s, **k: fig.text(x0 + k.pop("dx", 0), y, s, color=k.pop("color", COR["texto"]), **k)
    t(0.915, "VOTO PARA PRESIDENTE · 1º TURNO · 42 MUNICÍPIOS", size=9, color=COR["texto2"], family=DADOS)
    t(0.865, "A enchente de 2024 mudou o voto\nna Grande Porto Alegre?", size=23, weight="bold", va="top",
      linespacing=1.15)

    # os dois números: quanto a diferença PT − PL andou de 2022 para 2026, dentro e fora da água
    t(0.69, "Quanto a diferença PT − PL mudou de 2022 para 2026,\nnas mesmas seções eleitorais, em pontos", size=11,
      color=COR["texto2"], va="top", linespacing=1.3)
    for dx, v, rot in [(0, d["mud"], "dentro da área alagada"), (0.2, f["mud"], "fora dela")]:
        t(0.52, num(v), dx=dx, size=44, weight="bold")
        t(0.48, rot, dx=dx, size=11.5, color=COR["texto2"], va="top")

    y = 0.365
    fig.add_artist(plt.Line2D([x0, 0.96], [y + 0.035, y + 0.035], color=COR["texto"], lw=1.2))
    itens = [
        ("O voto andou igual dentro e fora da água",
         f"a diferença entre os dois, {num(R['dif_mud'])} ponto, é menor que a margem de acaso"),
        ("A distância entre os grupos já existia antes",
         f"{num(dist[0], False)} pontos em 2018, {num(dist[1], False)} em 2022 e {num(dist[2], False)} em 2026"),
    ]
    for a, b in itens:
        t(y, a, size=13, weight="bold", va="top")
        t(y - 0.05, b, size=11, color=COR["texto2"], va="top")
        y -= 0.11

    legenda(fig, x0, 0.105, fs=10)
    fig.text(0.96, 0.025, URL, family=DADOS, size=10.5, color=COR["texto"], ha="right")
    fig.text(0.012, 0.018, "Cada seta é um local de votação: para onde o voto andou de 2022 para 2026.",
             size=8.5, color=COR["texto2"], bbox=dict(facecolor=COR["fundo"], edgecolor="none", alpha=0.85, pad=3))

    out = SAIDA / "imagem_x.png"
    fig.savefig(out, dpi=DPI, facecolor=COR["fundo"])
    print(out, np.round(fig.get_size_inches() * DPI))


if __name__ == "__main__":
    main()
