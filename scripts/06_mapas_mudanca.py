"""Desenha as versões da mudança 2022 → 2026 a partir de saida/mudanca.gpkg e numeros_mudanca.json.

Peças, nos dois estilos de 03_mapas.py: tríptico 16:9 (2022 | 2026 | mudança com a área alagada),
carrossel 4:5 em 3 slides e zoom de Porto Alegre na mudança. O fundo, as cores da margem e os
textos-base vêm de 03_mapas.py. Saída: saida/imagens/mudanca_{estilo}_*.png
"""
import importlib
import json
import sys
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
COR, CRS, IMG, SAIDA = M.COR, M.CRS, M.IMG, M.SAIDA
pct, mil = M.pct, M.mil

# mudança na margem (PT − PL), em pontos percentuais
CORTES_MUD = [-14, -8, -2, 2]
CLASSES_MUD = [  # da esquerda (para o PT) para a direita (para o PL) na legenda; vizinhas conferidas no validador
    (4, "para o PT,\n2 ou mais", "#d4574a"),
    (3, "estável\n(menos de 2)", "#dedad2"),
    (2, "para o PL,\n2 a 8", "#8fb4e6"),
    (1, "para o PL,\n8 a 14", "#3f74c2"),
    (0, "para o PL,\n14 ou mais", "#0f3470"),
]
COR_MUD = {k: c for k, _, c in CLASSES_MUD}
# margem: mesmas faixas nos dois anos; nas peças com 2022 e 2026 juntos, as pontas levam o partido
# (o candidato do PL mudou, o partido não)
CLASSES_MARGEM = M.CLASSES
LADOS_PARTIDO = ("← PT à frente", "PL à frente →")
LADOS_2022 = ("← Lula (PT) à frente", "Jair Bolsonaro (PL) à frente →")

TITULO = "Enchente de 2024 × mudança no voto de 2022 para 2026 na Grande Porto Alegre"
SOBRE_45 = "Enchente de 2024 × mudança no voto de 2022 para 2026 na Grande Porto Alegre"


def subtitulo(estilo, n_mun):
    unidade = "em cada local de votação" if estilo == "pontos" else "no entorno de cada local de votação"
    return (f"1º turno para presidente, Lula (PT) × Jair Bolsonaro (PL) em 2022 e Lula (PT) × Flávio Bolsonaro (PL) em 2026, "
            f"{unidade}, na área do mapa ({n_mun} municípios, inteiros ou em parte)")


def mp(x):
    """Margem ou mudança com sinal, vírgula decimal."""
    return f"{x:+.1f}".replace(".", ",").replace("-", "−")


def carregar():
    L, N = M.carregar()
    g = SAIDA / "mudanca.gpkg"
    loc = gpd.read_file(g, layer="locais")
    are = gpd.read_file(g, layer="areas")
    for d in (loc, are):
        d["classe22"] = np.digitize(d.margem22.fillna(0), M.CORTES)
        d["classe26"] = np.digitize(d.margem26, M.CORTES)
        d["classe_mud"] = np.digitize(d.mudanca.fillna(0), CORTES_MUD)
    L["m_locais"] = loc.sort_values("validos26", ascending=False)
    L["m_areas"] = are
    NM = json.loads((SAIDA / "numeros_mudanca.json").read_text(encoding="utf-8"))
    return L, N, NM


# ---------- camadas ----------

def camada(ax, L, estilo, qual, smax, vmax, municipio=None):
    """qual: '22' (margem 2022), '26' (margem 2026) ou 'mud' (mudança)."""
    d = L["m_locais"] if estilo == "pontos" else L["m_areas"]
    if municipio:
        d = d[d.municipio == municipio]
    if qual == "22":
        d, cor, val = d[d.validos22 > 0], d.classe22.map(M.COR_CLASSE), "validos22"
    elif qual == "26":
        cor, val = d.classe26.map(M.COR_CLASSE), "validos26"
    else:
        d, cor, val = d[d.comparavel], d.classe_mud.map(COR_MUD), "validos26"
    cor = cor.reindex(d.index)
    if estilo == "pontos":
        ax.scatter(d.geometry.x, d.geometry.y, s=M.tamanho(d[val], smax, vmax), c=cor,
                   edgecolors=COR["fundo"], linewidths=0.5, zorder=5)
    else:
        d.plot(ax=ax, color=cor, edgecolor=COR["fundo"], lw=0.15, zorder=4)


def painel(ax, L, frame, estilo, qual, smax, vmax, fs_lago, municipio=None, destaque=None):
    M.base(ax, L, frame, destaque=destaque)
    camada(ax, L, estilo, qual, smax, vmax, municipio)
    if qual == "mud":
        M.mancha(ax, L["mancha_ufrgs"], estilo)
    M.rotulo_lago(ax, L, frame, fs=fs_lago)


# ---------- textos ----------

def eixo_livre(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return ax


def legenda_classes(fig, rect, classes, titulo, fs, estilo=None, mancha_x=None, lados=None):
    """Faixa de quadradinhos com rótulo embaixo; opcionalmente quem está à frente em cada ponta (lados)
    e a amostra da área alagada à direita."""
    ax = eixo_livre(fig, rect)
    ax.text(0, 0.95, titulo, fontsize=fs, color=COR["texto2"], va="top")
    fim = mancha_x - 0.03 if mancha_x else 1
    w = fim / len(classes)
    for i, (_, rot, cor) in enumerate(classes):
        ax.add_patch(plt.Rectangle((i * w, 0.45), w - 0.006, 0.17, color=cor))
        ax.text(i * w + w / 2, 0.36, rot, fontsize=fs - 1.5, ha="center", va="top", color=COR["texto"],
                linespacing=1.1)
    if lados:
        M.lados(ax, fim - 0.006, fs - 1.5, lados)
    if mancha_x:
        M.amostra_mancha(ax, mancha_x, 0.45, 0.06, 0.17, estilo)
        ax.text(mancha_x + 0.08, 0.535, "Área alagada\nem maio de 2024", fontsize=fs - 1.5, va="center",
                linespacing=1.2)


def bloco_mudanca(fig, rect, NM, fs, escopo="mapa", quebra=120, tres_colunas=False):
    """Mudança na margem dentro × fora, com a margem de cada ano embaixo; eleitorado numa 3ª coluna
    (tres_colunas) ou numa nota no pé do bloco."""
    if escopo == "mapa":
        d, f = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
        rot_fora = "No restante da área do mapa"
    else:
        d, f = NM["porto_alegre_criterios"]["ada"]["dentro"], NM["porto_alegre_criterios"]["ada"]["fora"]
        rot_fora = "No restante de Porto Alegre"
    ax = eixo_livre(fig, rect)
    y_num, y_det = (0.6, 0.2) if tres_colunas else (0.68, 0.44)
    xs = [0, 0.34, 0.68] if tres_colunas else [0, 0.5]
    for x, rot, s in [(xs[0], "Locais dentro da área alagada", d), (xs[1], rot_fora, f)]:
        ax.text(x, 0.97, rot, fontsize=fs - 3, color=COR["texto2"], va="top")
        ax.text(x, y_num, f"{mp(s['mudanca_margem'])} pontos", fontsize=fs + 4, weight="bold", va="center")
        ax.text(x, y_det, f"diferença PT − PL: {mp(s['margem_22'])} em 2022, {mp(s['margem_26'])} em 2026",
                fontsize=fs - 3.5, color=COR["texto2"], va="center")
    if tres_colunas:
        x = xs[2]
        ax.text(x, 0.97, "Eleitores aptos, de 2022 para 2026", fontsize=fs - 3, color=COR["texto2"], va="top")
        ax.text(x, y_num, f"{mp(d['mudanca_aptos_pct'])}% nos alagados, {mp(f['mudanca_aptos_pct'])}% no resto",
                fontsize=fs - 1, weight="bold", va="center")
        ax.text(x, y_det, f"comparecimento: {mp(d['mudanca_comparecimento'])} pontos nos alagados, "
                          f"{mp(f['mudanca_comparecimento'])} no resto", fontsize=fs - 3.5, color=COR["texto2"],
                va="center")
        return
    rod = (f"Eleitores aptos de 2022 para 2026: {mp(d['mudanca_aptos_pct'])}% nos locais alagados e "
           f"{mp(f['mudanca_aptos_pct'])}% no restante. Comparecimento: {pct(d['comparecimento_22'])} → "
           f"{pct(d['comparecimento_26'])} nos alagados e {pct(f['comparecimento_22'])} → "
           f"{pct(f['comparecimento_26'])} no restante.")
    ax.text(0, 0.0, "\n".join(textwrap.wrap(rod, quebra)), fontsize=fs - 3.5, color=COR["texto2"],
            va="bottom", linespacing=1.3)


def rodape(fig, y, NM, quebra, fs, estilo, fonte_mancha=M.FONTE_ADA):
    lg = NM["ligacao"]
    setores = " e setores do Censo 2022" if estilo == "areas" else ""
    t = (f"Fontes: TSE, votação por seção e locais de votação, 1º turno de 2022 e de 2026 · {fonte_mancha} · "
         f"IBGE, malha municipal 2025{setores} · SEMA-RS, base cartográfica 1:25.000. Comparação descritiva; não "
         f"mede o efeito da enchente sobre o voto. Cada seção eleitoral de 2022 é comparada com a mesma seção em "
         f"2026, no local onde votou em 2026. {lg['pontos_sem_cor']} locais novos ou com menos de "
         f"{NM['min_validos']} votos válidos ficam sem cor no mapa da mudança.")
    fig.text(0.025, y, "\n".join(textwrap.wrap(t, quebra)), fontsize=fs, color=COR["texto3"], va="top",
             linespacing=1.35)
    fig.text(0.975, y, M.ASSINATURA, fontsize=fs + 3, color=COR["texto2"], ha="right", va="top", weight="bold")


# ---------- versões ----------

def triptico(L, N, NM, vmax, estilo):
    W, H = 16, 9
    fig = plt.figure(figsize=(W, H), dpi=M.DPI, facecolor=COR["fundo"])
    frame = L["moldura"].total_bounds
    fig.text(0.025, 0.955, TITULO, fontsize=22, weight="bold", va="top")
    fig.text(0.025, 0.903, subtitulo(estilo, N["municipios_no_mapa"]), fontsize=12.5, color=COR["texto2"], va="top")
    w = 0.305
    h = w * W / M.proporcao(frame) / H
    y = 0.815 - h
    titulos = ["1  2022: Lula (PT) × Jair Bolsonaro (PL)", "2  2026: Lula (PT) × Flávio Bolsonaro (PL)", "3  Mudança de 2022 para 2026"]
    smax = 105
    for i, (x, qual) in enumerate(zip([0.025, 0.3475, 0.67], ["22", "26", "mud"])):
        ax = fig.add_axes([x, y, w, h])
        painel(ax, L, frame, estilo, qual, smax, vmax, fs_lago=7.5)
        ax.set_title(titulos[i], loc="left", fontsize=13, weight="bold", pad=7)
    legenda_classes(fig, [0.025, y - 0.125, 0.6275, 0.1], CLASSES_MARGEM,
                    "Diferença PT − PL (pontos percentuais dos votos válidos)", fs=10.5, lados=LADOS_PARTIDO)
    legenda_classes(fig, [0.67, y - 0.125, 0.305, 0.1], CLASSES_MUD,
                    "Mudança na diferença PT − PL, em pontos", fs=9.5, estilo=estilo, mancha_x=0.79)
    bloco_mudanca(fig, [0.025, 0.1, 0.95, y - 0.145 - 0.1], NM, fs=14, tres_colunas=True)
    rodape(fig, 0.075, NM, 190, fs=8, estilo=estilo)
    return M.salvar(fig, f"mudanca_{estilo}_triptico_16x9.png")


def slide(L, N, NM, vmax, i, estilo):
    titulos = ["Como votou cada lugar em 2022", "Como votou cada lugar em 2026", "O que mudou, e onde a água chegou"]
    fig, ax, (w_in, h_in) = M.figura_45(SOBRE_45, f"{i + 1}/3  {titulos[i]}", fs_titulo=21)
    frame = M.ajustar(L["moldura"].total_bounds, w_in, h_in)
    smax = 150
    painel(ax, L, frame, estilo, ["22", "26", "mud"][i], smax, vmax, fs_lago=9)
    if i < 2:
        ano, rival = ("2022", "Jair Bolsonaro") if i == 0 else ("2026", "Flávio Bolsonaro")
        legenda_classes(fig, [0.05, 0.245, 0.9, 0.085], CLASSES_MARGEM,
                        f"Diferença Lula (PT) − {rival} (PL), {ano}, em pontos percentuais dos votos válidos", fs=9.5,
                        lados=LADOS_2022 if i == 0 else M.LADOS)
        como = ("Cada círculo é um local de votação de 2026; o tamanho é o número de votos válidos."
                if estilo == "pontos" else
                "Cada área é o entorno de um local de votação de 2026, pintado só onde moram 100 ou mais\n"
                "pessoas por km² (Censo 2022).")
        if i == 0:
            como += "\nEm 2022, cada seção eleitoral aparece no local onde votou em 2026."
        fig.text(0.05, 0.215, como, fontsize=10.5, color=COR["texto2"], va="top", linespacing=1.4)
    else:
        legenda_classes(fig, [0.05, 0.255, 0.9, 0.075], CLASSES_MUD,
                        "Mudança na diferença PT − PL de 2022 para 2026, em pontos", fs=9, estilo=estilo,
                        mancha_x=0.75)
        bloco_mudanca(fig, [0.05, 0.105, 0.9, 0.14], NM, fs=14, quebra=120)
    rodape(fig, 0.085, NM, 140, fs=7.5, estilo=estilo)
    return M.salvar(fig, f"mudanca_{estilo}_carrossel_4x5_{i + 1}.png")


def zoom_poa(L, N, NM, vmax, estilo):
    poa = L["nucleo"][L["nucleo"].NM_MUN == "Porto Alegre"]
    fig, ax, (w_in, h_in) = M.figura_45(SOBRE_45, "Porto Alegre: o que mudou e onde a água chegou", fs_titulo=20)
    x0, y0, x1, y1 = poa.total_bounds
    frame = M.ajustar((x0 - 1200, y0 - 1200, x1 + 1200, y1 + 1200), w_in, h_in)
    painel(ax, L, frame, estilo, "mud", 240, vmax, fs_lago=10, municipio="Porto Alegre", destaque="Porto Alegre")
    b = L["bairros"]
    for _, r in b[b.nome.isin(M.BAIRROS_ZOOM)].dissolve("nome").reset_index().iterrows():
        q = r.geometry.representative_point()
        ax.text(q.x, q.y, M.BAIRROS_ZOOM[r.nome], fontsize=8.5, color=COR["texto"], ha="center",
                va="center", path_effects=M.HALO, zorder=8)
    legenda_classes(fig, [0.05, 0.255, 0.9, 0.075], CLASSES_MUD,
                    "Mudança na diferença PT − PL de 2022 para 2026, em pontos", fs=9, estilo=estilo,
                    mancha_x=0.75)
    bloco_mudanca(fig, [0.05, 0.105, 0.9, 0.14], NM, fs=14, escopo="poa", quebra=120)
    rodape(fig, 0.085, NM, 140, fs=7.5, estilo=estilo)
    return M.salvar(fig, f"mudanca_{estilo}_zoom_porto_alegre_4x5.png")


def main():
    L, N, NM = carregar()
    vmax = float(L["m_locais"][["validos22", "validos26"]].max().max())
    for velho in IMG.glob("mudanca_*.png"):
        velho.unlink()
    for estilo in M.ESTILOS:
        print(triptico(L, N, NM, vmax, estilo))
        for i in range(3):
            print(slide(L, N, NM, vmax, i, estilo))
        print(zoom_poa(L, N, NM, vmax, estilo))


if __name__ == "__main__":
    main()
