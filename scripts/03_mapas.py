"""Desenha as versões da imagem a partir de saida/camadas.gpkg e saida/numeros.json.

Versões: tríptico horizontal (1920x1080), carrossel 4:5 em 3 slides (1080x1350) e zoom de
Porto Alegre na sobreposição (1080x1350), este também numa variante com a simulação de 5,30 m.
Cada peça sai em dois estilos: "pontos" (um círculo por local, mancha em cinza) e "areas"
(entorno de cada local onde mora gente, mancha hachurada). Saída em saida/imagens/.
"""
import json
import textwrap
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import shapely
from shapely.geometry import Point, box

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"
IMG = SAIDA / "imagens"
IMG.mkdir(parents=True, exist_ok=True)
CRS = 31982
DPI = 120

plt.rcParams.update({"font.family": "Segoe UI", "font.size": 11, "text.color": "#0b0b0b",
                     "hatch.linewidth": 0.5})
ESTILOS = ["pontos", "areas"]
HACHURA = "////"

COR = {
    "fundo": "#fcfcfb", "texto": "#0b0b0b", "texto2": "#52514e", "texto3": "#8a8880",
    "terra": "#ecebe6", "vizinho": "#f6f5f2", "limite": "#c9c5bc", "agua": "#d9e4ec",
    "agua_txt": "#5f7a8c", "mancha": "#3a3a3a", "contorno": "#141414",
}
# margem = % Lula (PT) − % Flávio Bolsonaro (PL) (votos válidos), em pontos percentuais
CORTES = [-20, -5, 5, 20]
CLASSES = [  # da esquerda (Lula) para a direita (Flávio Bolsonaro) na legenda; quem está à frente vai em LADOS
    (4, "+20 ou mais", "#b8232b"),
    (3, "+5 a +20", "#f0947f"),
    (2, "menos de 5", "#d4d0c7"),
    (1, "+5 a +20", "#7eaee6"),
    (0, "+20 ou mais", "#123e7c"),
]
LADOS = ("← Lula (PT) à frente", "Flávio Bolsonaro (PL) à frente →")
COR_CLASSE = {k: c for k, _, c in CLASSES}
COR_LULA, COR_FLAVIO = COR_CLASSE[4], COR_CLASSE[0]

TITULO = "Enchente de maio de 2024 × 1º turno de 2026 na Grande Porto Alegre"
def subtitulo(N, estilo):
    unidade = "em cada local de votação" if estilo == "pontos" else "no entorno de cada local de votação"
    return (f"Voto para presidente, Lula (PT) × Flávio Bolsonaro (PL), {unidade}, e a área alagada na área do mapa "
            f"({N['municipios_no_mapa']} municípios, inteiros ou em parte)")
ASSINATURA = "Matheus Dalmolin"
FONTE_ADA = ("UFRGS/IPH, Possantti et al., Banco de dados das cheias da RH do Guaíba v1.4, área diretamente "
             "afetada em 6 e 8/5/2024 (CC BY 4.0)")
FONTE_530 = ("UFRGS/IPH, Possantti et al., Banco de dados das cheias da RH do Guaíba v1.4, simulação "
             "hidrostática de Porto Alegre com o Guaíba a 5,30 m (CC BY 4.0); fora de Porto Alegre, área "
             "diretamente afetada em 6 e 8/5/2024")
# rótulos dos municípios: (lon, lat, alinhamento)
ROTULOS_MUN = {
    "Novo Hamburgo": (-51.10, -29.69, "left"), "São Leopoldo": (-51.165, -29.765, "right"),
    "Sapucaia do Sul": (-51.135, -29.828, "left"), "Esteio": (-51.19, -29.858, "right"),
    "Nova Santa Rita": (-51.33, -29.845, "center"), "Canoas": (-51.19, -29.918, "right"),
    "Cachoeirinha": (-51.08, -29.945, "left"), "Gravataí": (-50.93, -29.925, "center"),
    "Alvorada": (-51.06, -30.0, "left"), "Porto Alegre": (-51.13, -30.09, "center"),
    "Eldorado do Sul": (-51.53, -30.07, "center"), "Guaíba": (-51.37, -30.18, "center"),
    "Montenegro": (-51.46, -29.69, "center"), "São Sebastião do Caí": (-51.375, -29.6, "center"),
    "Triunfo": (-51.69, -29.925, "center"), "Charqueadas": (-51.60, -29.975, "center"),
    "Viamão": (-51.02, -30.08, "center"),
}

BAIRROS_ZOOM = {  # nome na base (sem acento) -> rótulo
    "CENTRO HISTORICO": "Centro Histórico", "SARANDI": "Sarandi", "HUMAITA": "Humaitá",
    "NAVEGANTES": "Navegantes", "MENINO DEUS": "Menino Deus", "CIDADE BAIXA": "Cidade Baixa",
    "ARQUIPELAGO": "Arquipélago", "RESTINGA": "Restinga", "LAMI": "Lami", "PARTENON": "Partenon",
    "RUBEM BERTA": "Rubem Berta", "BELEM NOVO": "Belém Novo", "IPANEMA": "Ipanema",
}
HALO = [pe.withStroke(linewidth=2.6, foreground=COR["fundo"])]
AGUA_TXT = "em azul-claro, a água que já existia antes (Guaíba, rios e delta do Jacuí), que não conta como alagada."
LEITURA = {
    "pontos": ("Cada círculo é um local de votação; o tamanho é o número de votos válidos. Em cinza, a área "
               "alagada em maio de 2024;\n" + AGUA_TXT),
    "areas": ("Cada área é o entorno de um local de votação, pintado só onde moram 100 ou mais pessoas por km² "
              "(Censo 2022). Hachurada, a área\nalagada em maio de 2024; " + AGUA_TXT),
}
# layout dos formatos 4:5 (fração da figura): o mapa fica no mesmo lugar em todos os slides
MAPA_45 = [0.06, 0.345, 0.88, 0.545]


def pct(x):
    return f"{x:.1f}".replace(".", ",") + "%"


def mil(n):
    return f"{n:,.0f}".replace(",", ".")


def xy(lon, lat):
    p = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(CRS).iloc[0]
    return p.x, p.y


def carregar():
    g = SAIDA / "camadas.gpkg"
    L = {k: gpd.read_file(g, layer=k) for k in
         ["nucleo", "vizinhos", "moldura", "agua", "mancha_ufrgs", "mancha_poa530", "locais", "areas"]}
    pts = L["locais"]
    pts["classe"] = np.digitize(pts.margem, CORTES)
    L["locais"] = pts.sort_values("validos", ascending=False)
    a = L["areas"]
    a["classe"] = np.digitize(a.margem, CORTES)
    a["municipio"] = a.pid.map(pts.drop_duplicates("pid").set_index("pid").municipio)
    L["areas"] = a
    L["bairros"] = gpd.read_file(SAIDA / "bairros_poa.gpkg")
    N = json.loads((SAIDA / "numeros.json").read_text(encoding="utf-8"))
    return L, N


# ---------- camadas do mapa ----------

def base(ax, L, frame, destaque=None):
    ax.set_facecolor(COR["agua"])
    L["vizinhos"].plot(ax=ax, color=COR["vizinho"], edgecolor=COR["limite"], lw=0.4)
    nuc = L["nucleo"]
    if destaque:
        nuc[nuc.NM_MUN != destaque].plot(ax=ax, color=COR["vizinho"], edgecolor=COR["limite"], lw=0.5)
        nuc = nuc[nuc.NM_MUN == destaque]
    nuc.plot(ax=ax, color=COR["terra"], edgecolor=COR["limite"], lw=0.7)
    L["agua"].plot(ax=ax, color=COR["agua"], lw=0)
    x0, y0, x1, y1 = frame
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def mancha(ax, g, estilo="pontos"):
    if estilo == "pontos":
        g.plot(ax=ax, color=COR["mancha"], alpha=0.42, lw=0)
    else:
        g.plot(ax=ax, facecolor="none", edgecolor=COR["contorno"], hatch=HACHURA, lw=0, zorder=6)
    g.boundary.plot(ax=ax, color=COR["contorno"], lw=0.45, alpha=0.75, zorder=6)


def tamanho(validos, smax, vmax):
    return smax * np.asarray(validos) / vmax


def pontos(ax, p, smax, vmax):
    ax.scatter(p.geometry.x, p.geometry.y, s=tamanho(p.validos, smax, vmax),
               c=p.classe.map(COR_CLASSE), edgecolors=COR["fundo"], linewidths=0.5, zorder=5)


def voto(ax, L, estilo, smax, vmax, municipio=None):
    if estilo == "pontos":
        p = L["locais"]
        pontos(ax, p if municipio is None else p[p.municipio == municipio], smax, vmax)
    else:
        a = L["areas"]
        a = a if municipio is None else a[a.municipio == municipio]
        a.plot(ax=ax, color=a.classe.map(COR_CLASSE), edgecolor=COR["fundo"], lw=0.15, zorder=4)


def rotulos_municipios(ax, fs):
    for nome, (lon, lat, ha) in ROTULOS_MUN.items():
        ax.text(*xy(lon, lat), nome, fontsize=fs, color=COR["texto2"], ha=ha, va="center",
                path_effects=HALO, zorder=8)


def rotulo_lago(ax, L, frame, fs):
    """Rótulo no ponto mais aberto do maior corpo d'água visível (centro do maior círculo inscrito)."""
    agua = L["agua"].union_all().intersection(box(*frame))
    maior = max(getattr(agua, "geoms", [agua]), key=lambda g: g.area)
    x, y = shapely.maximum_inscribed_circle(maior, tolerance=50).coords[0]
    ax.text(x, y, "Lago Guaíba", fontsize=fs, color=COR["agua_txt"], style="italic",
            ha="center", va="center", zorder=8)


def proporcao(frame):
    x0, y0, x1, y1 = frame
    return (x1 - x0) / (y1 - y0)


# ---------- blocos de texto ----------

def amostra_mancha(ax, x, y, w, h, estilo):
    if estilo == "pontos":
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=COR["mancha"], alpha=0.42,
                                   edgecolor=COR["contorno"], lw=0.6))
    else:
        ax.add_patch(plt.Rectangle((x, y), w, h, facecolor="none", edgecolor=COR["contorno"],
                                   hatch=HACHURA, lw=0.6))


def lados(ax, x1, fs, rotulos=LADOS, y=0.36):
    """Linha de baixo da legenda de margem: quem está à frente em cada ponta da faixa de cores (de 0 a x1)."""
    for x, ha, t in [(0, "left", rotulos[0]), (x1, "right", rotulos[1])]:
        ax.annotate(t, (x, y), xytext=(0, -(fs + 3)), textcoords="offset points", ha=ha, va="top", fontsize=fs,
                    color=COR["texto2"])


def legenda(fig, rect, estilo, smax, vmax, fs, titulo=True, com_mancha=True):
    """Classes de margem, tamanhos de referência e a mancha, numa faixa só."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    topo = 0.95
    if titulo:
        ax.text(0, topo, "Diferença Lula (PT) − Flávio Bolsonaro (PL), em pontos percentuais",
                fontsize=fs, color=COR["texto2"], va="top")
    w = 0.6 / len(CLASSES)
    for i, (_, rot, cor) in enumerate(CLASSES):
        ax.add_patch(plt.Rectangle((i * w, 0.45), w - 0.004, 0.17, color=cor))
        ax.text(i * w + w / 2, 0.36, rot, fontsize=fs - 1.5, ha="center", va="top", color=COR["texto"])
    lados(ax, len(CLASSES) * w - 0.004, fs - 1.5)
    xs = 0.655
    if estilo == "pontos":
        ax.text(xs, topo, "Votos válidos", fontsize=fs, color=COR["texto2"], va="top")
        for j, v in enumerate([1000, 4000, 7000]):
            cx = xs + 0.018 + j * 0.05
            ax.scatter(cx, 0.535, s=tamanho(v, smax, vmax), color="none", edgecolors=COR["texto2"],
                       linewidths=0.8, clip_on=False)
            ax.text(cx, 0.36, mil(v), fontsize=fs - 1.5, ha="center", va="top")
    else:
        ax.text(xs, 0.535, "Área = entorno do local,\nsó onde mora gente", fontsize=fs - 1.5, va="center",
                color=COR["texto2"], linespacing=1.2)
    if com_mancha:
        xm = 0.84
        amostra_mancha(ax, xm, 0.45, 0.04, 0.17, estilo)
        ax.text(xm + 0.05, 0.535, "Área alagada\nem maio de 2024", fontsize=fs - 1.5, va="center",
                linespacing=1.2)


def bloco_numero(fig, rect, N, fs, escopo="nucleo", quebra=200):
    """Dentro × fora lado a lado, com o tamanho do grupo embaixo."""
    if escopo == "nucleo":
        d, f = N["criterios"]["ada"]["dentro"], N["criterios"]["ada"]["fora"]
        rot_fora = "No restante da área do mapa"
        rodape = (f"{mil(d['aptos'] / 1000)} mil eleitores ({pct(100 * d['aptos'] / N['aptos_mapa_total'])} "
                  f"do eleitorado da área do mapa) votam nos {d['locais']} locais dentro da área alagada.")
    else:
        crit = "poa530" if escopo == "poa530" else "ada"
        d, f = (N["porto_alegre_criterios"][crit][k] for k in ("dentro", "fora"))
        rot_fora = "No restante de Porto Alegre"
        rodape = f"{mil(d['aptos'] / 1000)} mil eleitores votam nos {d['locais']} locais dentro da área alagada."
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # tabelinha: candidatos nas colunas, grupos nas linhas (os nomes completos não cabem lado a lado)
    xs = [0.36, 0.62]
    for x, nome, cor in [(xs[0], "Lula (PT)", COR_LULA), (xs[1], "Flávio Bolsonaro (PL)", COR_FLAVIO)]:
        ax.scatter(x + 0.008, 0.9, marker="s", s=fs * 6, color=cor, clip_on=False)
        ax.text(x + 0.028, 0.9, nome, fontsize=fs - 3.5, color=COR["texto2"], va="center")
    for y, rot, s in [(0.63, "Locais dentro da área alagada", d), (0.34, rot_fora, f)]:
        ax.text(0, y, "\n".join(textwrap.wrap(rot, 20)), fontsize=fs - 3, color=COR["texto2"], va="center",
                linespacing=1.15)
        for x, chave in zip(xs, ["pct_lula", "pct_flavio"]):
            ax.text(x + 0.028, y, pct(s[chave]), fontsize=fs + 4, weight="bold", va="center")
    ax.text(0, 0.0, "\n".join(textwrap.wrap(rodape, quebra)), fontsize=fs - 3.5, color=COR["texto2"],
            va="bottom", linespacing=1.3)


def rodape(fig, y, N, quebra, fs, estilo, fonte_mancha=FONTE_ADA):
    ex = N["excluidos_sem_coord"]
    setores = " e setores do Censo 2022" if estilo == "areas" else ""
    t = (f"Fontes: TSE, votação por seção e locais de votação, 1º turno 2026 · {fonte_mancha} · IBGE, malha "
         f"municipal 2025{setores} · SEMA-RS, base cartográfica 1:25.000. Comparação descritiva; não mede o efeito da "
         f"enchente sobre o voto. Local alagado = ponto do local de votação dentro da mancha, sem a água "
         f"permanente. {ex['locais']} locais sem coordenada no TSE ficaram de fora "
         f"({pct(ex['pct_validos'])} dos votos válidos).")
    fig.text(0.025, y, "\n".join(textwrap.wrap(t, quebra)), fontsize=fs, color=COR["texto3"], va="top",
             linespacing=1.35)
    fig.text(0.975, y, ASSINATURA, fontsize=fs + 3, color=COR["texto2"], ha="right", va="top", weight="bold")


# ---------- versões ----------

def triptico(L, N, vmax, estilo):
    W, H = 16, 9
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=COR["fundo"])
    frame = L["moldura"].total_bounds
    fig.text(0.025, 0.955, TITULO, fontsize=22, weight="bold", va="top")
    fig.text(0.025, 0.903, subtitulo(N, estilo), fontsize=12.5, color=COR["texto2"], va="top")
    w = 0.305
    h = w * W / proporcao(frame) / H
    topo = 0.815
    y = topo - h
    titulos = ["1  Voto no 1º turno de 2026", "2  Área alagada em maio de 2024", "3  As duas camadas juntas"]
    smax = 105
    for i, x in enumerate([0.025, 0.3475, 0.67]):
        ax = fig.add_axes([x, y, w, h])
        base(ax, L, frame)
        if i in (0, 2):
            voto(ax, L, estilo, smax, vmax)
        if i in (1, 2):
            mancha(ax, L["mancha_ufrgs"], estilo)
        if i == 1:
            rotulos_municipios(ax, fs=7)
        rotulo_lago(ax, L, frame, fs=7.5)
        ax.set_title(titulos[i], loc="left", fontsize=13, weight="bold", pad=7)
    legenda(fig, [0.025, y - 0.135, 0.62, 0.11], estilo, smax, vmax, fs=10.5)
    bloco_numero(fig, [0.67, y - 0.235, 0.305, 0.21], N, fs=14, quebra=72)
    fig.text(0.025, y - 0.165, LEITURA[estilo], fontsize=10.5, color=COR["texto2"], va="top", linespacing=1.4)
    rodape(fig, 0.075, N, 190, fs=8, estilo=estilo)
    return salvar(fig, f"{estilo}_triptico_16x9.png")


def ajustar(frame, w_in, h_in):
    """Amplia a moldura para a proporção do eixo, sem cortar nada."""
    x0, y0, x1, y1 = frame
    alvo = w_in / h_in
    cx, cy, lw_, lh = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if lw_ / lh < alvo:
        lw_ = lh * alvo
    else:
        lh = lw_ / alvo
    return (cx - lw_ / 2, cy - lh / 2, cx + lw_ / 2, cy + lh / 2)


def figura_45(sobre, titulo, fs_titulo=21):
    W, H = 9, 11.25
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=COR["fundo"])
    fig.text(0.05, 0.965, sobre, fontsize=11, color=COR["texto2"], va="top")
    fig.text(0.05, 0.935, titulo, fontsize=fs_titulo, weight="bold", va="top")
    ax = fig.add_axes(MAPA_45)
    return fig, ax, (MAPA_45[2] * W, MAPA_45[3] * H)


def slide(L, N, vmax, i, estilo):
    titulos = ["Como votou cada local de votação", "Onde a água chegou em maio de 2024",
               "As duas camadas juntas"]
    fig, ax, (w_in, h_in) = figura_45(TITULO, f"{i + 1}/3  {titulos[i]}")
    frame = ajustar(L["moldura"].total_bounds, w_in, h_in)
    base(ax, L, frame)
    smax = 150
    if i in (0, 2):
        voto(ax, L, estilo, smax, vmax)
    if i in (1, 2):
        mancha(ax, L["mancha_ufrgs"], estilo)
    if i == 1:
        rotulos_municipios(ax, fs=9)
    rotulo_lago(ax, L, frame, fs=9)
    if i == 0:
        legenda(fig, [0.05, 0.245, 0.9, 0.085], estilo, smax, vmax, fs=9.5, com_mancha=False)
        como = ("Cada círculo é um local de votação; o tamanho é o número de votos válidos." if estilo == "pontos"
                else "Cada área é o entorno de um local de votação, pintado só onde moram 100 ou mais\n"
                     "pessoas por km² (Censo 2022).")
        fig.text(0.05, 0.215, como + "\n1º turno para presidente, 4 de outubro de 2026.", fontsize=10.5,
                 color=COR["texto2"], va="top", linespacing=1.4)
    elif i == 1:
        txt = ("Área diretamente afetada em 6 e 8 de maio de 2024, segundo a UFRGS/IPH. A água que já existia "
               "antes (Guaíba, rios e delta do Jacuí) aparece em azul-claro e não conta como alagada.")
        ax_l = fig.add_axes([0.05, 0.255, 0.9, 0.075])
        ax_l.set_xlim(0, 1)
        ax_l.set_ylim(0, 1)
        ax_l.axis("off")
        amostra_mancha(ax_l, 0, 0.35, 0.06, 0.3, estilo)
        ax_l.text(0.075, 0.5, "Área alagada em maio de 2024", fontsize=11, va="center")
        ax_l.add_patch(plt.Rectangle((0.42, 0.35), 0.06, 0.3, facecolor=COR["agua"], lw=0))
        ax_l.text(0.495, 0.5, "Água que já existia antes", fontsize=11, va="center")
        fig.text(0.05, 0.235, "\n".join(textwrap.wrap(txt, 95)), fontsize=10.5, color=COR["texto2"], va="top",
                 linespacing=1.4)
    else:
        legenda(fig, [0.05, 0.255, 0.9, 0.075], estilo, smax, vmax, fs=9, titulo=False)
        bloco_numero(fig, [0.05, 0.105, 0.9, 0.14], N, fs=14, quebra=120)
    rodape(fig, 0.085, N, 140, fs=7.5, estilo=estilo)
    return salvar(fig, f"{estilo}_carrossel_4x5_{i + 1}.png")


def zoom_poa(L, N, vmax, estilo, variante="ada"):
    poa = L["nucleo"][L["nucleo"].NM_MUN == "Porto Alegre"]
    if variante == "poa530":
        poa_geom = poa.union_all()
        g = gpd.GeoDataFrame(geometry=[
            L["mancha_poa530"].union_all().intersection(poa_geom)
            .union(L["mancha_ufrgs"].union_all().difference(poa_geom))], crs=CRS)
        titulo = "Porto Alegre, com a simulação do Guaíba a 5,30 m"
        nome, fonte = f"{estilo}_zoom_porto_alegre_4x5_simulacao530.png", FONTE_530
    else:
        g = L["mancha_ufrgs"]
        titulo = "Porto Alegre: voto e área alagada"
        nome, fonte = f"{estilo}_zoom_porto_alegre_4x5.png", FONTE_ADA

    fig, ax, (w_in, h_in) = figura_45(TITULO, titulo, fs_titulo=20)
    x0, y0, x1, y1 = poa.total_bounds
    frame = ajustar((x0 - 1200, y0 - 1200, x1 + 1200, y1 + 1200), w_in, h_in)
    base(ax, L, frame, destaque="Porto Alegre")
    voto(ax, L, estilo, 240, vmax, municipio="Porto Alegre")
    mancha(ax, g, estilo)
    b = L["bairros"]
    for _, r in b[b.nome.isin(BAIRROS_ZOOM)].dissolve("nome").reset_index().iterrows():
        q = r.geometry.representative_point()
        ax.text(q.x, q.y, BAIRROS_ZOOM[r.nome], fontsize=8.5, color=COR["texto"], ha="center",
                va="center", path_effects=HALO, zorder=8)
    rotulo_lago(ax, L, frame, fs=10)
    legenda(fig, [0.05, 0.255, 0.9, 0.075], estilo, 240, vmax, fs=9, titulo=False)
    bloco_numero(fig, [0.05, 0.105, 0.9, 0.14], N, fs=14, escopo=variante, quebra=120)
    rodape(fig, 0.085, N, 140, fs=7.5, estilo=estilo, fonte_mancha=fonte)
    return salvar(fig, nome)


def salvar(fig, nome):
    out = IMG / nome
    fig.savefig(out, dpi=DPI, facecolor=COR["fundo"])
    plt.close(fig)
    return out


def main():
    L, N = carregar()
    vmax = float(L["locais"].validos.max())
    for velho in [p for e in ESTILOS for p in IMG.glob(f"{e}_*.png")]:
        velho.unlink()
    for estilo in ESTILOS:
        print(triptico(L, N, vmax, estilo))
        for i in range(3):
            print(slide(L, N, vmax, i, estilo))
        print(zoom_poa(L, N, vmax, estilo))
        print(zoom_poa(L, N, vmax, estilo, variante="poa530"))


if __name__ == "__main__":
    main()
