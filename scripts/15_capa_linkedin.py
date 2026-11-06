"""Capa do artigo no LinkedIn (1920 x 1080): o mapa dos locais de votação em fundo escuro, com os dois números grandes.

No mesmo desenho da capa das urnas (secoes-2turno-2026, scripts/15_capa_linkedin.py): à direita, o miolo da Grande
Porto Alegre com a mancha da enchente e um ponto por local de votação, na cor de para onde o voto andou de 2022 para
2026 (pontos e não setas: na capa, pequena, as setas se embolavam); os locais da área alagada saem maiores e com
halo, os de fora pequenos. À esquerda, em letra grande, a queda da diferença PT − PL dentro e fora da área alagada;
um degradê deixa o texto legível onde encosta no mapa. Os números vêm de docs/dados/resumo.json, os mesmos do cartão do X.

No feed, o LinkedIn corta a capa para 1,91:1 (cerca de 37 px em cima e embaixo). Mapa e texto ficam dentro de
MARGEM, com folga. Para conferir, rode com --corte: a saída ganha linhas tracejadas onde o feed corta.

Com --og, faz a imagem do artigo no site pessoal: o mesmo desenho com o endereço do texto, cortado para 1,91:1
(dentro de MARGEM, como no feed do LinkedIn) e reduzido a 1200 x 630, gravado direto em
C:/dev/dalmolin.dev/public/textos/enchente-e-voto/artigo_og.png (a capa do LinkedIn não é tocada).

Uso: python -P scripts/15_capa_linkedin.py [--corte | --og]   (depois de 05 e 13)
Saída: saida/capa_linkedin.png (com --corte, saida/capa_linkedin_corte.png, só para conferência)
"""
import importlib
import io
import json
import sys
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
MM = importlib.import_module("06_mapas_mudanca")
SAIDA = M.SAIDA

FUNDO, TINTA, TINTA2 = "#0e1014", "#f5f6f8", "#b4b9c1"
TERRA, LIMITE, AGUA = FUNDO, "#252a32", "#07080a"  # a terra some no fundo; rios e lago um pouco mais escuros
MANCHA, CONTORNO, CONTORNO_TXT = "#243b52", "#6f9cc4", "#8fb4d6"  # a mancha num azul-ardósia, bem visível no escuro
PT, PL = "#ee6f61", "#5f97ea"  # as cores da capa das urnas
FONTE, DADOS = "Segoe UI", "Consolas"
MARGEM = 0.075  # fração da altura livre em cima e embaixo (o corte do feed é ~0,035)
MAPA = [0.43, MARGEM, 0.555, 1 - 2 * MARGEM]
CENTRO, ALTURA = (480_000, 6_687_000), 62_000  # miolo: Porto Alegre a Novo Hamburgo, em metros (EPSG 31982)
ROTULOS = ["Novo Hamburgo", "Canoas", "Porto Alegre", "Gravataí"]  # os outros batem no texto
ROTULO_MANCHA = (0.25, 0.35)  # em fração do mapa: na parte alagada de Eldorado do Sul, sem locais por perto
OG = "--og" in sys.argv
URL = "dalmolin.dev/textos/enchente-e-voto" if OG else "matheusgsd.github.io/enchente-votos"
OG_DEST = Path(r"C:\dev\dalmolin.dev") / "public" / "textos" / "enchente-e-voto" / "artigo_og.png"


def num(v):
    return f"{v:+.1f}".replace(".", ",").replace("-", "−")


def mapa(fig, L):
    ax = fig.add_axes(MAPA)
    W, H = fig.get_size_inches()
    w = ALTURA * (MAPA[2] * W) / (MAPA[3] * H)
    x0, y0, x1, y1 = CENTRO[0] - w / 2, CENTRO[1] - ALTURA / 2, CENTRO[0] + w / 2, CENTRO[1] + ALTURA / 2
    ax.set_facecolor(AGUA)
    L["vizinhos"].plot(ax=ax, color=TERRA, edgecolor=LIMITE, lw=0.4)
    L["nucleo"].plot(ax=ax, color=TERRA, edgecolor=LIMITE, lw=0.6)
    L["agua"].plot(ax=ax, color=AGUA, lw=0)
    L["mancha_ufrgs"].plot(ax=ax, color=MANCHA, lw=0)
    L["mancha_ufrgs"].boundary.plot(ax=ax, color=CONTORNO, lw=0.5, alpha=0.8)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    halo = [pe.withStroke(linewidth=3, foreground=FUNDO)]
    for nome in ROTULOS:
        lon, lat, ha = M.ROTULOS_MUN[nome]
        ax.text(*M.xy(lon, lat), nome, fontsize=8, color=TINTA2, ha=ha, va="center", path_effects=halo, zorder=9)

    # um ponto por local, na cor de para onde o voto andou: os de fora pequenos, os da área alagada maiores e com halo
    pts = L["m_locais"]
    for alagado, tam, alfa in [(False, 5, 0.55), (True, 26, 1.0)]:
        g = pts[(pts.ada == alagado) & pts.comparavel & pts.mudanca.notna()]
        cor = np.where(g.mudanca < 0, PL, PT)
        x, y = g.geometry.x, g.geometry.y
        if alagado:
            ax.scatter(x, y, s=tam * 5, c=cor, alpha=0.18, lw=0, zorder=7)
        ax.scatter(x, y, s=tam, c=cor, alpha=alfa, lw=0.5 if alagado else 0, edgecolors=FUNDO, zorder=8 if alagado else 6)
    ax.text(*ROTULO_MANCHA, "área alagada\nem maio de 2024", fontsize=9, color=CONTORNO_TXT, ha="center",
            va="center", style="italic", linespacing=1.2, path_effects=halo, zorder=9, transform=ax.transAxes)
    # bordas do recorte esfumadas no fundo, para o mapa não virar um retângulo
    ny, nx = 300, 300
    yy, xx = np.mgrid[0:1:ny * 1j, 0:1:nx * 1j]
    borda = np.minimum.reduce([xx / 0.12, (1 - xx) / 0.06, yy / 0.1, (1 - yy) / 0.1])
    rgba = np.zeros((ny, nx, 4))
    rgba[..., :3] = [14 / 255, 16 / 255, 20 / 255]
    rgba[..., 3] = (1 - np.clip(borda, 0, 1)) ** 1.5
    ax.imshow(rgba, extent=(x0, x1, y0, y1), origin="lower", zorder=10, interpolation="bilinear")


def main():
    L, _, _ = MM.carregar()
    R = json.loads((M.RAIZ / "docs/dados/resumo.json").read_text(encoding="utf-8"))

    fig = plt.figure(figsize=(9.6, 5.4), dpi=200, facecolor=FUNDO)
    mapa(fig, L)
    # degradê para o texto ler bem onde encosta no mapa
    g = fig.add_axes([0, 0, 0.62, 1], zorder=1)
    cm = LinearSegmentedColormap.from_list("g", [(14 / 255, 16 / 255, 20 / 255, 1), (14 / 255, 16 / 255, 20 / 255, 0)])
    g.imshow(np.linspace(0, 1, 256)[None, :] ** 1.8, aspect="auto", cmap=cm, extent=(0, 1, 0, 1))
    g.axis("off")

    t = lambda x, y, s, **k: fig.text(x, y, s, family=k.pop("family", FONTE), color=k.pop("color", TINTA), zorder=2, **k)
    t(0.05, 0.855, "ENCHENTE DE 2024 · VOTO PARA PRESIDENTE · TSE", size=12, color=TINTA2, family=DADOS)
    t(0.05, 0.805, "A enchente mudou o voto", size=34, weight="bold", va="top")
    t(0.05, 0.695, "no primeiro turno de 2026?", size=22, weight="bold", va="top")
    t(0.05, 0.605, "Dentro e fora da água, ele andou junto.", size=20, va="top")
    t(0.05, 0.465, "Quanto a diferença PT − PL mudou de 2022 para 2026, em pontos", size=13, color=TINTA2)
    for x, v, rot in [(0.045, R["dentro"]["mud"], "dentro da área alagada"), (0.30, R["fora"]["mud"], "fora dela")]:
        t(x, 0.29, num(v), size=62, weight="bold")
        t(x + 0.005, 0.255, rot, size=15, color=TINTA2, va="top")
    # legenda: os pontos com o mesmo tamanho e halo do mapa
    lg = fig.add_axes([0, 0, 1, 1], facecolor="none", zorder=2)
    lg.set_xlim(0, 1)
    lg.set_ylim(0, 1)
    lg.axis("off")
    y = 0.15
    for x, cor, tam, rot in [(0.05, PL, 26, "para o PL"), (0.155, PT, 26, "para o PT"),
                             (0.27, TINTA2, 26, "dentro da área alagada"), (0.48, TINTA2, 5, "fora dela")]:
        if tam > 5:
            lg.scatter(x + 0.006, y + 0.008, s=tam * 5, c=cor, alpha=0.18, lw=0)
        lg.scatter(x + 0.006, y + 0.008, s=tam, c=cor, lw=0)
        t(x + 0.02, y, rot, size=12, color=TINTA2, va="baseline")
    t(0.05, MARGEM + 0.008, URL, size=12, color=TINTA2, family=DADOS)

    if OG:
        from PIL import Image

        buf = io.BytesIO()
        fig.savefig(buf, dpi=200, facecolor=FUNDO, format="png")
        im = Image.open(buf).convert("RGB")
        w, h = im.size
        alto = round(w * 630 / 1200)
        topo = (h - alto) // 2
        OG_DEST.parent.mkdir(parents=True, exist_ok=True)
        im.crop((0, topo, w, topo + alto)).resize((1200, 630), Image.LANCZOS).save(OG_DEST, optimize=True)
        print(OG_DEST)
        return
    out = SAIDA / "capa_linkedin.png"
    fig.savefig(out, dpi=200, facecolor=FUNDO)
    print(out)
    if "--corte" in sys.argv:
        corte = (1 - 1920 / 1.91 / 1080) / 2
        for yy in (corte, 1 - corte):
            fig.add_artist(plt.Line2D([0, 1], [yy, yy], color="#ffd54a", lw=1.2, ls="--", zorder=5))
        fig.savefig(SAIDA / "capa_linkedin_corte.png", dpi=200, facecolor=FUNDO)
        print(SAIDA / "capa_linkedin_corte.png")


if __name__ == "__main__":
    main()
