"""Versão dos mapas que pinta só os locais de votação dentro da área alagada; os outros ficam em contorno cinza.

Peças, nos dois estilos de 03_mapas.py: voto de 2026 e mudança de 2022 para 2026, cada um em 4:5, e os dois
lado a lado em 16:9. Local alagado = ponto do local dentro da mancha da UFRGS (o mesmo critério dos números).
Lê o mesmo que 06_mapas_mudanca.py. Saída: saida/imagens/alagados_{estilo}_*.png
"""
import importlib
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
MM = importlib.import_module("06_mapas_mudanca")
COR, IMG = M.COR, M.IMG
pct, mp = M.pct, MM.mp

COR_FORA = "#c2beb5"  # contorno dos locais fora da área alagada
CLASSES_26 = M.CLASSES
LEG_26 = "Diferença Lula (PT) − Flávio Bolsonaro (PL) em 2026, só nos locais dentro da área alagada (pontos percentuais)"
LEG_MUD = "Mudança na diferença PT − PL de 2022 para 2026, só nos locais dentro da área alagada (pontos)"


def camada_alagados(ax, L, estilo, qual, smax, vmax, municipio=None):
    """qual: '26' (margem de 2026) ou 'mud' (mudança). Locais fora da mancha só em contorno cinza."""
    d = L["m_locais"] if estilo == "pontos" else L["m_areas"]
    if municipio:
        d = d[d.municipio == municipio]
    fora, dentro = d[~d.ada], d[d.ada]
    if qual == "26":
        cor = dentro.classe26.map(M.COR_CLASSE)
    else:
        dentro = dentro[dentro.comparavel]
        cor = dentro.classe_mud.map(MM.COR_MUD)
    if estilo == "pontos":
        ax.scatter(fora.geometry.x, fora.geometry.y, s=M.tamanho(fora.validos26, smax, vmax), facecolors="none",
                   edgecolors=COR_FORA, linewidths=0.4, zorder=4)
        ax.scatter(dentro.geometry.x, dentro.geometry.y, s=M.tamanho(dentro.validos26, smax, vmax), c=cor,
                   edgecolors=COR["fundo"], linewidths=0.5, zorder=5)
    else:
        fora.plot(ax=ax, facecolor="none", edgecolor=COR_FORA, lw=0.2, zorder=4)
        dentro.plot(ax=ax, color=cor, edgecolor=COR["fundo"], lw=0.15, zorder=5)


def amostra_fora(ax, x, y, w, h, estilo):
    if estilo == "pontos":
        ax.scatter([x + w / 2], [y + h / 2], s=70, facecolors="none", edgecolors=COR_FORA, linewidths=0.8,
                   clip_on=False)
    else:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="none", edgecolor=COR_FORA, lw=0.8))


def legenda_alagados(fig, rect, classes, titulo, fs, estilo):
    """Classes de cor (só os alagados), amostra da mancha e amostra dos locais de fora, numa faixa só.
    Na margem de 2026, as pontas dizem quem está à frente."""
    ax = MM.eixo_livre(fig, rect)
    ax.text(0, 0.95, titulo, fontsize=fs, color=COR["texto2"], va="top")
    w = 0.6 / len(classes)
    for i, (_, rot, cor) in enumerate(classes):
        ax.add_patch(plt.Rectangle((i * w, 0.45), w - 0.006, 0.17, color=cor))
        ax.text(i * w + w / 2, 0.36, rot, fontsize=fs - 1.5, ha="center", va="top", color=COR["texto"],
                linespacing=1.1)
    if classes is CLASSES_26:
        M.lados(ax, 0.6 - 0.006, fs - 1.5)
    M.amostra_mancha(ax, 0.64, 0.45, 0.04, 0.17, estilo)
    ax.text(0.69, 0.535, "Área alagada\nem maio de 2024", fontsize=fs - 1.5, va="center", linespacing=1.2)
    amostra_fora(ax, 0.83, 0.45, 0.04, 0.17, estilo)
    ax.text(0.88, 0.535, "Locais fora da\nárea alagada", fontsize=fs - 1.5, va="center", linespacing=1.2)


def mapa(ax, L, frame, estilo, qual, smax, vmax, fs_lago):
    M.base(ax, L, frame)
    camada_alagados(ax, L, estilo, qual, smax, vmax)
    M.mancha(ax, L["mancha_ufrgs"], estilo)
    M.rotulo_lago(ax, L, frame, fs=fs_lago)


def numeros_curtos(N, NM, qual):
    """Uma linha com o número que acompanha cada mapa no 16:9."""
    if qual == "26":
        d, f = N["criterios"]["ada"]["dentro"], N["criterios"]["ada"]["fora"]
        return (f"Locais alagados: Lula {pct(d['pct_lula'])} × Flávio Bolsonaro {pct(d['pct_flavio'])}. "
                f"Restante: Lula {pct(f['pct_lula'])} × Flávio Bolsonaro {pct(f['pct_flavio'])}.")
    d, f = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
    return (f"Mudança na diferença PT − PL: {mp(d['mudanca_margem'])} pontos nos locais alagados e "
            f"{mp(f['mudanca_margem'])} no restante.")


def peca_45(L, N, NM, vmax, estilo, qual):
    if qual == "26":
        fig, ax, (w_in, h_in) = M.figura_45(M.TITULO, "Só os locais alagados: voto em 2026", fs_titulo=21)
    else:
        fig, ax, (w_in, h_in) = M.figura_45(MM.SOBRE_45, "Só os locais alagados: o que mudou desde 2022",
                                            fs_titulo=21)
    frame = M.ajustar(L["moldura"].total_bounds, w_in, h_in)
    mapa(ax, L, frame, estilo, qual, 150, vmax, fs_lago=9)
    if qual == "26":
        legenda_alagados(fig, [0.05, 0.255, 0.9, 0.075], CLASSES_26, LEG_26, 9, estilo)
        M.bloco_numero(fig, [0.05, 0.105, 0.9, 0.14], N, fs=14, quebra=120)
        M.rodape(fig, 0.085, N, 140, fs=7.5, estilo=estilo)
    else:
        legenda_alagados(fig, [0.05, 0.255, 0.9, 0.075], MM.CLASSES_MUD, LEG_MUD, 9, estilo)
        MM.bloco_mudanca(fig, [0.05, 0.105, 0.9, 0.14], NM, fs=14, quebra=120)
        MM.rodape(fig, 0.085, NM, 140, fs=7.5, estilo=estilo)
    nome = "voto_2026" if qual == "26" else "mudanca"
    return M.salvar(fig, f"alagados_{estilo}_{nome}_4x5.png")


def diptico(L, N, NM, vmax, estilo):
    W, H = 16, 9
    fig = plt.figure(figsize=(W, H), dpi=M.DPI, facecolor=COR["fundo"])
    frame = L["moldura"].total_bounds
    fig.text(0.025, 0.955, "Só os locais dentro da área alagada: voto em 2026 e mudança desde 2022",
             fontsize=22, weight="bold", va="top")
    fig.text(0.025, 0.903, "Grande Porto Alegre. Pintados só os locais de votação cujo ponto fica dentro da área "
                           "alagada em maio de 2024; os outros aparecem em contorno cinza.",
             fontsize=12.5, color=COR["texto2"], va="top")
    w = 0.37
    h = w * W / M.proporcao(frame) / H
    topo = 0.83
    y = topo - h
    for x, qual, tit, classes, leg in [(0.06, "26", "1  Voto em 2026: Lula (PT) × Flávio Bolsonaro (PL)", CLASSES_26,
                                        LEG_26),
                                       (0.53, "mud", "2  Mudança de 2022 para 2026", MM.CLASSES_MUD, LEG_MUD)]:
        ax = fig.add_axes([x, y, w, h])
        mapa(ax, L, frame, estilo, qual, 105, vmax, fs_lago=7.5)
        ax.set_title(tit, loc="left", fontsize=13, weight="bold", pad=7)
        legenda_alagados(fig, [x, y - 0.09, w, 0.08], classes, leg.split(", só")[0], 9, estilo)
        fig.text(x, y - 0.105, "\n".join(textwrap.wrap(numeros_curtos(N, NM, qual), 80)), fontsize=11.5,
                 va="top", linespacing=1.3)
    MM.rodape(fig, 0.075, NM, 190, fs=8, estilo=estilo)
    return M.salvar(fig, f"alagados_{estilo}_diptico_16x9.png")


def main():
    L, N, NM = MM.carregar()
    vmax = float(L["m_locais"][["validos22", "validos26"]].max().max())
    for velho in IMG.glob("alagados_*.png"):
        velho.unlink()
    for estilo in M.ESTILOS:
        print(diptico(L, N, NM, vmax, estilo))
        print(peca_45(L, N, NM, vmax, estilo, "26"))
        print(peca_45(L, N, NM, vmax, estilo, "mud"))


if __name__ == "__main__":
    main()
