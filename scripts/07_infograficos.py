"""Infográficos com os números das partes 1 e 2: carrossel 4:5 de 9 cartões e um resumo 16:9.

Lê saida/numeros.json (voto de 2026), saida/numeros_mudanca.json (2022 → 2026) e saida/numeros_2018.json
(2018, 2022 e 2026 nas mesmas seções, de 10_tendencia_2018.py). Cores dos candidatos,
fundo e assinatura vêm de 03_mapas.py; a área alagada e o restante ganham um par próprio (conferido no
validador da skill dataviz, também contra o vermelho e o azul dos candidatos).
Saída: saida/imagens/numeros_*.png
"""
import importlib
import json
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
MM = importlib.import_module("06_mapas_mudanca")
COR, IMG, SAIDA, DPI = M.COR, M.IMG, M.SAIDA, M.DPI
pct, mil, mp = M.pct, M.mil, MM.mp

COR_ALAGADO, COR_RESTO = "#0a8fa3", "#b0761c"  # água × terra seca
COR_OUTROS = "#d4d0c7"
SOBRE = "Enchente de 2024 × voto para presidente na Grande Porto Alegre"
TOTAL = 9
MIN_APTOS_CIDADE = 5000  # cidades com pelo menos isso de eleitores em locais alagados (2026)
FONTE_TSE = "TSE, votação por seção e locais de votação, 1º turno de {anos}"
FONTE_ADA = ("UFRGS/IPH, Possantti et al., Banco de dados das cheias da RH do Guaíba v1.4, área diretamente "
             "afetada em 6 e 8/5/2024 (CC BY 4.0)")
NOTA_ALAGADO = "Local alagado = ponto do local de votação dentro da mancha, sem a água permanente."
NOTA_SECAO = "Cada seção eleitoral de 2022 é comparada com a mesma seção em 2026."
NOTA_SECAO_18 = "Cada seção eleitoral é comparada com ela mesma em 2018, 2022 e 2026."
ANOS_18 = [("18", "2018", "Fernando Haddad (PT) ×\nJair Bolsonaro (PSL)"),
           ("22", "2022", "Lula (PT) ×\nJair Bolsonaro (PL)"),
           ("26", "2026", "Lula (PT) ×\nFlávio Bolsonaro (PL)")]
NOTA_CENARIO = ("O cenário político muda de uma eleição para outra: candidatos, partidos e alianças não são os mesmos. "
                "Por isso a altura das linhas não se compara de um ano para outro; o que se compara é a distância "
                "entre elas.")
NOTA_FIM = "Comparação descritiva; não mede o efeito da enchente sobre o voto."
# nomes do TSE -> nome curto para o cartão das seções que mudaram de local
NOMES = {
    "FORO TRABALHISTA DE PORTO ALEGRE": "Foro Trabalhista",
    "ESCOLA ESTADUAL PRESIDENTE ROOSEVELT": "E. E. Presidente Roosevelt",
    "ESC EST ENS MEDIO TEREZA FRANCESCUTTI": "E. E. Tereza Francescutti",
    "ASSOCIAÇÃO PESTALOZZI DE CANOAS": "Associação Pestalozzi",
    "ESCOLA ESTADUAL MARECHAL FLORIANO PEIXOTO": "E. E. Marechal Floriano Peixoto",
    "UFCSPA (SEÇÕES MAL. FLORIANO PEIXOTO)": "UFCSPA",
    "CENTRO SOCIAL MADRE REGINA": "Centro Social Madre Regina",
    "EEEF AYRTON SENNA": "E. E. Ayrton Senna",
    "COLEGIO ULBRA SAO JOAO": "Colégio Ulbra São João",
    "ESCOLA MUN. DE ENS. FUNDAMENTAL JOÃO PALMA DA SILVA": "E. M. João Palma da Silva",
    "ESC. MUN. DE ENS. FUND. DAVID RIEGEL NETO": "E. M. David Riegel Neto",
    "E.M.E.F. GETÚLIO VARGAS": "E. M. Getúlio Vargas",
    "E. E. E. F. CASTRO ALVES": "E. E. Castro Alves",
    "E.M.E.F. PADRE LUIZ DE NADAL": "E. M. Padre Luiz de Nadal",
    "ESCOLA ESTADUAL ALBINO HACKMANN": "E. E. Albino Hackmann",
    "E.M.E.F. RIO GRANDE DO SUL": "E. M. Rio Grande do Sul",
    "SAFE": "SAFE",
    "ESCOLA ESTADUAL OSCAR SCHMITT - I.DAS FLORES": "E. E. Oscar Schmitt",
    "INST. DE ED. INFANTIL ANJO DAS FLORES (SEÇÕES ESC. OSCAR SCHMITT)": "Inst. Anjo das Flores",
}


def num(x):
    return f"{x:.1f}".replace(".", ",")


def mil_k(n):
    """391227 -> '391 mil'; 2684639 -> '2,68 milhões'."""
    return f"{n / 1e6:.2f}".replace(".", ",") + " milhões" if n >= 1e6 else f"{mil(n / 1000)} mil"


def saldo(n):
    """-4493 -> '−4.493'."""
    return f"{n:+,.0f}".replace(",", ".").replace("-", "−")


def numero_rotulo(ax, x, y, cor, valor, rot, fs_num=24, fs_rot=13):
    """Marcador da cor do grupo, número grande e o rótulo logo depois do número."""
    marcador(ax, x + 0.012, y, cor, 13)
    t = ax.text(x + 0.04, y, valor, fontsize=fs_num, weight="bold", va="center")
    ax.annotate(rot, (1, 0.5), xycoords=t, xytext=(10, 0), textcoords="offset points", fontsize=fs_rot,
                va="center", color=COR["texto2"])


def nome_curto(s):
    return NOMES.get(s, s.title())


def eixo_livre(fig, rect, xlim=(0, 1), ylim=(0, 1)):
    ax = fig.add_axes(rect)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return ax


def marcador(ax, x, y, cor, fs, transform=None):
    ax.scatter([x], [y], s=fs * 7, color=cor, clip_on=False, transform=transform or ax.transData, zorder=5)


def legenda_grupos(fig, x, y, fs, resto="restante da área do mapa"):
    ax = eixo_livre(fig, [x, y, 0.9, 0.025])
    marcador(ax, 0.008, 0.5, COR_ALAGADO, fs)
    ax.text(0.025, 0.5, "locais dentro da área alagada", fontsize=fs, va="center")
    marcador(ax, 0.39, 0.5, COR_RESTO, fs)
    ax.text(0.407, 0.5, resto, fontsize=fs, va="center")


# ---------- gráficos (servem ao 4:5 e ao 16:9) ----------

def barras_voto(fig, rect, N, fs, altura=0.2):
    """Barras 100% de votos válidos: Lula | outros | Flávio Bolsonaro, dentro e fora."""
    d, f = N["criterios"]["ada"]["dentro"], N["criterios"]["ada"]["fora"]
    ax = eixo_livre(fig, rect, xlim=(0, 100))
    for y, rot, s in [(0.6, "Locais dentro da área alagada", d), (0.12, "Restante da área do mapa", f)]:
        ax.text(0, y + altura + 0.04, rot, fontsize=fs, color=COR["texto2"], va="bottom")
        outros = 100 - s["pct_lula"] - s["pct_flavio"]
        x = 0
        for w, cor, txt, tc in [(s["pct_lula"], M.COR_LULA, f"Lula (PT)\n{pct(s['pct_lula'])}", "white"),
                                (outros, COR_OUTROS, pct(outros), COR["texto"]),
                                (s["pct_flavio"], M.COR_FLAVIO, f"Flávio Bolsonaro (PL)\n{pct(s['pct_flavio'])}", "white")]:
            ax.add_patch(plt.Rectangle((x, y), w, altura, facecolor=cor, edgecolor=COR["fundo"], lw=2))
            ax.text(x + w / 2, y + altura / 2, txt, ha="center", va="center", color=tc,
                    fontsize=fs + (1 if tc == "white" else -1), weight="bold" if tc == "white" else "normal",
                    linespacing=1.15)
            x += w


def inclinacao(fig, rect, NM, fs, chave="ada", escopo="criterios"):
    """Diferença PT − PL em 2022 e 2026, uma linha por grupo."""
    d, f = NM[escopo][chave]["dentro"], NM[escopo][chave]["fora"]
    ax = eixo_livre(fig, rect, xlim=(-0.6, 2.05), ylim=(-12.5, 4.5))
    ax.axhline(0, color=COR["texto3"], lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(2.05, 0.35, "↑ PT à frente", fontsize=fs - 2, color=COR["texto3"], ha="right", va="bottom")
    ax.text(2.05, -0.35, "↓ PL à frente", fontsize=fs - 2, color=COR["texto3"], ha="right", va="top")
    for s, cor, nome in [(f, COR_RESTO, "restante"), (d, COR_ALAGADO, "área alagada")]:
        ys = [s["margem_22"], s["margem_26"]]
        ax.plot([0, 1], ys, color=cor, lw=2.5, solid_capstyle="round", zorder=3)
        ax.scatter([0, 1], ys, s=75, color=cor, edgecolors=COR["fundo"], linewidths=1.5, zorder=4)
        ax.text(-0.08, ys[0], mp(ys[0]), ha="right", va="center", fontsize=fs + 1, weight="bold")
        ax.text(1.08, ys[1], mp(ys[1]), ha="left", va="center", fontsize=fs + 1, weight="bold")
        ax.annotate(nome, (1.08, ys[1]), xytext=(fs * 3.3, 0), textcoords="offset points", ha="left",
                    va="center", fontsize=fs, color=COR["texto2"])
    for x, ano, quem in [(0, "2022", "Lula (PT) ×\nJair Bolsonaro (PL)"),
                         (1, "2026", "Lula (PT) ×\nFlávio Bolsonaro (PL)")]:
        ax.text(x, -12.5, ano, ha="center", va="top", fontsize=fs + 1, weight="bold")
        ax.annotate(quem, (x, -12.5), xytext=(0, -(fs + 6)), textcoords="offset points", ha="center",
                    va="top", fontsize=fs - 2, color=COR["texto2"])


def barras_aptos(fig, rect, NM, fs, altura=0.2, escopo="criterios", chave="ada", rot_fora="Restante da área do mapa"):
    """Queda de eleitores aptos (mesmas seções), em %, com o número absoluto ao lado."""
    d, f = NM[escopo][chave]["dentro"], NM[escopo][chave]["fora"]
    vmax = max(-d["mudanca_aptos_pct"], -f["mudanca_aptos_pct"])
    ax = eixo_livre(fig, rect, xlim=(0, vmax * 2.6))
    for y, rot, s, cor in [(0.6, "Locais dentro da área alagada", d, COR_ALAGADO), (0.12, rot_fora, f, COR_RESTO)]:
        v = s["mudanca_aptos_pct"]
        ax.text(0, y + altura + 0.04, rot, fontsize=fs, color=COR["texto2"], va="bottom")
        ax.add_patch(plt.Rectangle((0, y), -v, altura, facecolor=cor, lw=0))
        t = ax.text(-v + vmax * 0.04, y + altura / 2, f"{mp(v)}%", fontsize=fs + 5, weight="bold", va="center")
        ax.annotate(f"{mil_k(s['aptos_22'])} → {mil_k(s['aptos_26'])}", (1, 0.5), xycoords=t, xytext=(6, 0),
                    textcoords="offset points", fontsize=fs - 1, color=COR["texto2"], va="center")


def halteres(fig, rect, linhas, xlim, ticks, fs, cab_resto="resto", fmt=mp, rot_quebra=34, unidade=""):
    """Uma linha por item: ponto do alagado e do restante no mesmo eixo, com os valores em colunas à direita.
    linhas: [(rótulo, detalhe ou None, valor_alagado, valor_restante)]"""
    x0, y0, w, h = rect
    ax = fig.add_axes([x0 + 0.33, y0, 0.31, h])
    n = len(linhas)
    ax.set_xlim(*xlim)
    ax.set_ylim(n - 0.4, -0.75)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_yticks([])
    ax.set_xticks(ticks)
    ax.set_xticklabels([("0" if t == 0 else fmt(t).replace(",0", "")) + unidade for t in ticks], fontsize=fs - 2,
                       color=COR["texto3"])
    ax.tick_params(axis="x", length=0, pad=4)
    for t in ticks:
        ax.axvline(t, color=COR["limite"] if t else COR["texto3"], lw=0.6 if t else 1, zorder=0)
    ax.set_facecolor(COR["fundo"])
    tr = ax.get_yaxis_transform()  # x em fração do eixo, y em dado
    colunas = [(1.18, "alagado"), (1.45, cab_resto), (1.74, "diferença")]
    for x, cab in colunas:
        ax.text(x, -0.75, cab, transform=tr, ha="center", va="bottom", fontsize=fs - 2, color=COR["texto2"])
    for i, (rot, det, va, vr) in enumerate(linhas):
        ax.plot([va, vr], [i, i], color=COR["texto3"], lw=1.2, zorder=2)
        ax.scatter([vr], [i], s=90, color=COR_RESTO, edgecolors=COR["fundo"], linewidths=1.2, zorder=3)
        ax.scatter([va], [i], s=90, color=COR_ALAGADO, edgecolors=COR["fundo"], linewidths=1.2, zorder=4)
        # com detalhe: rótulo logo acima da linha do ponto e detalhe logo abaixo (distância fixa em pontos)
        ax.annotate("\n".join(textwrap.wrap(rot, rot_quebra)), (-1.06, i), xycoords=tr,
                    xytext=(0, 1 if det else 0), textcoords="offset points", ha="left",
                    va="bottom" if det else "center", fontsize=fs, linespacing=1.15)
        if det:
            ax.annotate(det, (-1.06, i), xycoords=tr, xytext=(0, -3), textcoords="offset points", ha="left",
                        va="top", fontsize=fs - 2.5, color=COR["texto2"])
        for (x, _), v, peso in zip(colunas, [va, vr, va - vr], ["normal", "normal", "bold"]):
            ax.text(x, i, fmt(v), transform=tr, ha="center", va="center", fontsize=fs, weight=peso)
    return ax


def comparecimento(fig, rect, NM, fs):
    """Comparecimento 2022 → 2026 por grupo, num eixo estreito (pontos, não barras)."""
    d, f = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
    x0, y0, w, h = rect
    wa = w - 0.33 - 0.17  # deixa espaço à direita para a mudança
    ax = fig.add_axes([x0 + 0.33, y0, wa, h])
    ax.set_xlim(74.5, 80.5)
    ax.set_ylim(1.6, -0.6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_yticks([])
    ticks = [75, 76, 77, 78, 79, 80]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t}%" for t in ticks], fontsize=fs - 2, color=COR["texto3"])
    ax.tick_params(axis="x", length=0, pad=4)
    for t in ticks:
        ax.axvline(t, color=COR["limite"], lw=0.6, zorder=0)
    ax.set_facecolor(COR["fundo"])
    tr = ax.get_yaxis_transform()
    for i, (rot, s, cor) in enumerate([("Locais dentro da\nárea alagada", d, COR_ALAGADO),
                                       ("Restante da área\ndo mapa", f, COR_RESTO)]):
        a, b = s["comparecimento_22"], s["comparecimento_26"]
        ax.annotate("", xy=(b, i), xytext=(a, i), arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.7",
                    color=cor, lw=2, shrinkA=7, shrinkB=7))
        ax.scatter([a], [i], s=90, facecolor=COR["fundo"], edgecolor=cor, linewidths=2, zorder=4)
        ax.scatter([b], [i], s=90, color=cor, zorder=4)
        ax.text(a, i - 0.3, f"{pct(a)}\n2022", ha="center", va="bottom", fontsize=fs - 2, linespacing=1.1)
        ax.text(b, i - 0.3, f"{pct(b)}\n2026", ha="center", va="bottom", fontsize=fs - 2, linespacing=1.1)
        ax.text(-0.33 / wa, i, rot, transform=tr, ha="left", va="center", fontsize=fs, linespacing=1.15)
        ax.text(1.04, i, f"{mp(b - a)} pontos", transform=tr, ha="left", va="center", fontsize=fs, weight="bold")


def tres_eleicoes(fig, rect, N18, fs, xmin=-0.85):
    """Diferença PT − PSL/PL em 2018, 2022 e 2026 nas mesmas seções, uma linha por grupo, com os valores numa
    tabelinha embaixo dos anos (linha da distância entre os grupos em negrito)."""
    d, f = N18["criterios"]["ada"]["dentro"], N18["criterios"]["ada"]["fora"]
    y0 = -36
    ax = eixo_livre(fig, rect, xlim=(xmin, 2.75), ylim=(y0, 6))
    ax.plot([-0.25, 2.25], [0, 0], color=COR["texto3"], lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(2.75, 0.5, "↑ PT à frente", fontsize=fs - 2, color=COR["texto3"], ha="right", va="bottom")
    ax.text(2.75, -0.5, "↓ PSL/PL à frente", fontsize=fs - 2, color=COR["texto3"], ha="right", va="top")
    # a enchente cai entre a eleição de 2022 e a de 2026
    ax.plot([1.6, 1.6], [y0 + 1, 3.5], color=COR["texto3"], lw=1, ls=(0, (1.5, 2.5)), zorder=1)
    ax.text(1.6, 4, "enchente\nmaio de 2024", ha="center", va="bottom", fontsize=fs - 2.5, color=COR["texto2"],
            linespacing=1.1)
    for s, cor, nome in [(f, COR_RESTO, "restante"), (d, COR_ALAGADO, "área alagada")]:
        ys = [s[f"margem_{a}"] for a, _, _ in ANOS_18]
        ax.plot([0, 1, 2], ys, color=cor, lw=2.5, solid_capstyle="round", zorder=3)
        ax.scatter([0, 1, 2], ys, s=75, color=cor, edgecolors=COR["fundo"], linewidths=1.5, zorder=4)
        ax.annotate(nome, (2, ys[2]), xytext=(10, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=fs, color=COR["texto2"])
    for x, (_, ano, quem) in enumerate(ANOS_18):
        ax.text(x, y0, ano, ha="center", va="top", fontsize=fs + 1, weight="bold")
        ax.annotate(quem, (x, y0), xytext=(0, -(fs + 6)), textcoords="offset points", ha="center", va="top",
                    fontsize=fs - 2.5, color=COR["texto2"], linespacing=1.1)
    topo = -(fs + 6) - 2.4 * (fs - 2.5) - fs * 1.4
    for i, (rot, s, cor) in enumerate([("alagados", d, COR_ALAGADO), ("restante", f, COR_RESTO),
                                       ("distância", None, None)]):
        tr = offset_copy(ax.transData, fig=fig, y=topo - i * fs * 1.75, units="points")
        if cor:
            marcador(ax, xmin + 0.04, y0, cor, fs * 0.8, transform=tr)
        ax.text(xmin + (0.1 if cor else 0), y0, rot, transform=tr, va="center", fontsize=fs,
                weight="normal" if cor else "bold")
        for x, (a, _, _) in enumerate(ANOS_18):
            v = s[f"margem_{a}"] if s else d[f"margem_{a}"] - f[f"margem_{a}"]
            ax.text(x, y0, mp(v), transform=tr, ha="center", va="center", fontsize=fs,
                    weight="normal" if s else "bold")
    return ax


def antes_depois(fig, rect, N18, chave, fs, unidade="", rot_w=0.3):
    """Variação antes (2018 → 2022) e depois da enchente (2022 → 2026), uma barra por grupo, mesmas seções."""
    d, f = N18["criterios"]["ada"]["dentro"], N18["criterios"]["ada"]["fora"]
    periodos = [("18_22", "2018 → 2022", "antes da enchente"), ("22_26", "2022 → 2026", "depois da enchente")]
    vals = [s[f"{chave}_{p}"] for p, _, _ in periodos for s in (d, f)]
    lo, hi = min(0, *vals), max(0, *vals)
    x0, y0, w, h = rect
    ax = fig.add_axes([x0 + rot_w, y0, w - rot_w, h])
    pad = (hi - lo) * 0.3
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(len(periodos) - 0.45, -0.55)
    ax.axis("off")
    ax.axvline(0, color=COR["texto3"], lw=1, zorder=1)
    tr = ax.get_yaxis_transform()
    for i, (p, rot, quando) in enumerate(periodos):
        for dy, s, cor in [(-0.19, d, COR_ALAGADO), (0.19, f, COR_RESTO)]:
            v = s[f"{chave}_{p}"]
            ax.barh(i + dy, v, height=0.34, color=cor, zorder=2)
            ax.text(v + (1 if v >= 0 else -1) * (hi - lo) * 0.03, i + dy, mp(v) + unidade, va="center",
                    ha="left" if v >= 0 else "right", fontsize=fs, weight="bold")
        ax.text(-rot_w / (w - rot_w), i - 0.1, rot, transform=tr, va="bottom", fontsize=fs, weight="bold")
        ax.text(-rot_w / (w - rot_w), i - 0.05, quando, transform=tr, va="top", fontsize=fs - 1.5,
                color=COR["texto2"])
    return ax


# ---------- moldura dos cartões ----------

def cartao(n, titulo, sub, quebra=84):
    fig = plt.figure(figsize=(9, 11.25), dpi=DPI, facecolor=COR["fundo"])
    fig.text(0.05, 0.965, SOBRE, fontsize=11, color=COR["texto2"], va="top")
    fig.text(0.05, 0.935, f"{n}/{TOTAL}  {titulo}", fontsize=20, weight="bold", va="top")
    fig.text(0.05, 0.888, "\n".join(textwrap.wrap(sub, quebra)), fontsize=12, color=COR["texto2"], va="top",
             linespacing=1.4)
    return fig


def nota(fig, y, txt, quebra=100, fs=11):
    fig.text(0.05, y, "\n".join(textwrap.wrap(txt, quebra)), fontsize=fs, color=COR["texto2"], va="top",
             linespacing=1.4)


def rodape(fig, anos="2022 e de 2026", extra="", secao=True, y=0.075, quebra=165, fs=7.5, x0=0.05, x1=0.95):
    """secao: True (nota de 2022 → 2026), False (sem nota) ou o texto da nota."""
    partes = [f"Fontes: {FONTE_TSE.format(anos=anos)} · {FONTE_ADA}{extra}.", NOTA_ALAGADO,
              (NOTA_SECAO if secao is True else secao) if secao else "", NOTA_FIM]
    t = " ".join(p for p in partes if p)
    fig.text(x0, y, "\n".join(textwrap.wrap(t, quebra)), fontsize=fs, color=COR["texto3"], va="top",
             linespacing=1.35)
    fig.text(x1, y + 0.03, M.ASSINATURA, fontsize=fs + 3, color=COR["texto2"], ha="right", va="top", weight="bold")


def salvar(fig, nome):
    out = IMG / nome
    fig.savefig(out, dpi=DPI, facecolor=COR["fundo"])
    plt.close(fig)
    return out


# ---------- cartões 4:5 ----------

def c1_voto(N, NM):
    d = N["criterios"]["ada"]["dentro"]
    fig = cartao(1, "Como votaram os locais alagados em 2026",
                 "1º turno de 2026 para presidente, Lula (PT) × Flávio Bolsonaro (PL), votos válidos. Locais dentro "
                 f"da área alagada em maio de 2024 × restante da área do mapa ({N['municipios_no_mapa']} "
                 "municípios da Grande Porto Alegre, inteiros ou em parte).")
    fig.text(0.05, 0.775, f"{mil(d['aptos'] / 1000)} mil", fontsize=54, weight="bold", va="center")
    fig.text(0.44, 0.775, "\n".join(textwrap.wrap(
        f"eleitores votam nos {d['locais']} locais de votação que ficaram dentro da área alagada: "
        f"{pct(100 * d['aptos'] / N['aptos_mapa_total'])} do eleitorado da área do mapa.", 42)),
        fontsize=13, va="center", linespacing=1.35)
    barras_voto(fig, [0.05, 0.42, 0.9, 0.27], N, fs=13)
    fig.text(0.05, 0.41, "Em cinza, os outros candidatos somados.", fontsize=10.5, color=COR["texto2"], va="top")
    ax = eixo_livre(fig, [0.05, 0.26, 0.9, 0.1])
    ax.text(0, 0.95, "Diferença Lula − Flávio Bolsonaro, em pontos percentuais", fontsize=11, color=COR["texto2"], va="top")
    f = N["criterios"]["ada"]["fora"]
    for x, s, cor, rot in [(0, d, COR_ALAGADO, "locais alagados"), (0.5, f, COR_RESTO, "restante")]:
        numero_rotulo(ax, x, 0.42, cor, mp(s["pct_lula"] - s["pct_flavio"]), rot)
    md, mf = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
    nota(fig, 0.215, f"Nos mesmos lugares, a diferença entre os dois grupos já existia em 2022: Lula − Jair Bolsonaro "
                     f"ficou em {mp(md['margem_22'])} nos locais alagados e em {mp(mf['margem_22'])} no restante "
                     "(próximo cartão).")
    rodape(fig, anos="2026", secao=False)
    return salvar(fig, "numeros_4x5_1.png")


def c2_mudanca(NM):
    d, f = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
    fig = cartao(2, "Diferença PT − PL em 2022 e em 2026",
                 "Em pontos percentuais dos votos válidos, nos mesmos lugares. Lula (PT) disputou com Jair "
                 "Bolsonaro (PL) em 2022 e com Flávio Bolsonaro (PL) em 2026.")
    inclinacao(fig, [0.1, 0.475, 0.82, 0.35], NM, fs=12.5)
    ax = eixo_livre(fig, [0.05, 0.315, 0.9, 0.08])
    ax.text(0, 0.95, "Mudança de 2022 para 2026", fontsize=11, color=COR["texto2"], va="top")
    for x, s, cor, rot in [(0, d, COR_ALAGADO, "locais alagados"), (0.5, f, COR_RESTO, "restante")]:
        numero_rotulo(ax, x, 0.3, cor, mp(s["mudanca_margem"]), rot)
    # cada candidato
    ax = eixo_livre(fig, [0.05, 0.13, 0.9, 0.16])
    ax.text(0, 0.98, "Cada candidato, % dos votos válidos", fontsize=11, color=COR["texto2"], va="top")
    for x, nome, k22, k26, cor in [(0, "Lula (PT)", "pct_lula_22", "pct_lula_26", M.COR_LULA),
                                   (0.5, "PL (Jair → Flávio Bolsonaro)", "pct_n22_22", "pct_n22_26", M.COR_FLAVIO)]:
        ax.add_patch(plt.Rectangle((x, 0.66), 0.022, 0.1, color=cor))
        ax.text(x + 0.035, 0.71, nome, fontsize=12, weight="bold", va="center")
        for y, s, cg, rot in [(0.38, d, COR_ALAGADO, "alagados"), (0.08, f, COR_RESTO, "restante")]:
            marcador(ax, x + 0.012, y, cg, 9)
            ax.text(x + 0.035, y, f"{rot}: {pct(s[k22])} → {pct(s[k26])}", fontsize=11.5, va="center")
            ax.text(x + 0.40, y, mp(s[k26] - s[k22]), fontsize=11.5, va="center", weight="bold", ha="right")
    rodape(fig)
    return salvar(fig, "numeros_4x5_2.png")


def c3_tres_eleicoes(N18):
    d, f = N18["criterios"]["ada"]["dentro"], N18["criterios"]["ada"]["fora"]
    fig = cartao(3, "E antes da enchente? 2018, 2022 e 2026",
                 "Diferença PT − PSL/PL, em pontos percentuais dos votos válidos: PSL em 2018, PL em 2022 e 2026. Só "
                 "as seções eleitorais que existem nas três eleições.")
    tres_eleicoes(fig, [0.05, 0.43, 0.82, 0.4], N18, fs=12.5)
    difs = [d[f"margem_{a}"] - f[f"margem_{a}"] for a, _, _ in ANOS_18]
    nota(fig, 0.25, f"{NOTA_CENARIO} A distância entre os locais alagados e o restante ficou entre "
                     f"{mp(min(difs))} e {mp(max(difs))} pontos nas três eleições, antes e depois da enchente. Os valores "
                     "diferem um pouco dos do cartão 2 porque entram só as seções que já existiam em 2018.")
    rodape(fig, anos="2018, de 2022 e de 2026", secao=NOTA_SECAO_18)
    return salvar(fig, "numeros_4x5_3.png")


def cidades_18(N18):
    """Por cidade: (nome, aptos alagados 2026, distância alagado − resto na variação de aptos antes, e depois)."""
    r = [(m, v["dentro"]["aptos_26"],
          v["dentro"]["mudanca_aptos_pct_18_22"] - v["fora"]["mudanca_aptos_pct_18_22"],
          v["dentro"]["mudanca_aptos_pct_22_26"] - v["fora"]["mudanca_aptos_pct_22_26"])
         for m, v in N18["por_municipio"].items()]
    return sorted(r, key=lambda x: -x[1])


def texto_cidades_18(N18):
    """Resumo por cidade: em quantas a perda a mais dos alagados cresceu depois da enchente, e as exceções."""
    cs = cidades_18(N18)
    pior = [m for m, _, a, b in cs if b < a - 0.5]
    melhor = [m for m, _, a, b in cs if b > a + 0.5]
    m0, _, a0, b0 = cs[0]
    assert a0 < -1 and abs(b0 - a0) < 0.5, "a cidade maior deixou de ter a mesma distância antes e depois"
    e = lambda xs: ", ".join(xs[:-1]) + " e " + xs[-1] if len(xs) > 1 else xs[0]
    return (f"Dentro de cada cidade, a perda a mais de eleitores nos locais alagados cresceu depois da enchente em "
            f"{len(pior)} das {len(cs)} cidades. Em {m0}, a com mais eleitores em locais alagados, eles já cresciam "
            f"{num(-a0)} pontos menos que o resto da cidade de 2018 para 2022, e a distância ficou igual depois"
            + (f"; em {e(melhor)}, diminuiu." if melhor else "."))


def c7_antes_depois(N18):
    d, f = N18["criterios"]["ada"]["dentro"], N18["criterios"]["ada"]["fora"]
    fig = cartao(7, "Eleitores antes e depois da enchente",
                 "Variação de 2018 para 2022 (antes) e de 2022 para 2026 (depois), nas seções eleitorais que existem "
                 "nas três eleições. Aptos = registrados na seção; abstenção = aptos que não votaram.")
    legenda_grupos(fig, 0.05, 0.8, 11)
    fig.text(0.05, 0.765, "Eleitores aptos, variação em %", fontsize=13, weight="bold", va="top")
    antes_depois(fig, [0.05, 0.565, 0.9, 0.175], N18, "mudanca_aptos_pct", fs=12.5, unidade="%")
    fig.text(0.05, 0.525, "Abstenção, mudança em pontos percentuais", fontsize=13, weight="bold", va="top")
    antes_depois(fig, [0.05, 0.325, 0.9, 0.175], N18, "mudanca_abstencao", fs=12.5)
    nota(fig, 0.29, f"No conjunto, antes da enchente os dois grupos ganharam eleitores no mesmo ritmo e a abstenção "
                    f"subiu praticamente o mesmo; depois, os locais alagados perderam mais eleitores "
                    f"({mp(d['mudanca_aptos_pct_22_26'])}% × {mp(f['mudanca_aptos_pct_22_26'])}%) e tiveram mais "
                    f"abstenção. {texto_cidades_18(N18)} De 2022 para 2026, os números diferem um pouco dos do cartão 6 "
                    "porque entram só as seções que já existiam em 2018.")
    rodape(fig, anos="2018, de 2022 e de 2026", secao=NOTA_SECAO_18)
    return salvar(fig, "numeros_4x5_7.png")


def linhas_criterios(NM):
    c = NM["criterios"]
    itens = [("Mancha da UFRGS, local dentro", "a usada nos mapas", c["ada"]),
             ("Mancha da UFRGS, até 500 m", "local a até 500 m da mancha", c["ada_500"]),
             ("Mancha do governo do RS, local dentro", "imagens de 23/5/2024", c["spgg"]),
             ("Mancha do governo do RS, até 500 m", "local a até 500 m da mancha", c["spgg_500"]),
             ("Peso pela população alagada", "no entorno de cada local (Censo 2022)", NM["ponderado_populacao"]),
             ("Mancha da UFRGS, local de 2022", "cada seção pelo local onde votava em 2022",
              NM["pela_posicao_de_2022"])]
    return itens


def c4_criterios(NM):
    itens = linhas_criterios(NM)
    fig = cartao(4, "A mudança com outras definições de área alagada",
                 "Mudança na diferença PT − PL de 2022 para 2026, em pontos percentuais. Cada linha define "
                 "\"local alagado\" de um jeito; negativo = andou para o PL.")
    legenda_grupos(fig, 0.05, 0.795, 11, resto="restante da área do mapa")
    linhas = [(r, det, s["dentro"]["mudanca_margem"], s["fora"]["mudanca_margem"]) for r, det, s in itens]
    halteres(fig, [0.05, 0.27, 0.9, 0.49], linhas, (-12, 0), [-12, -8, -4, 0], fs=11.5, rot_quebra=40)
    difs = [a - b for _, _, a, b in linhas]
    nota(fig, 0.215, f"Diferença = mudança nos alagados − mudança no restante. Vai de {mp(min(difs))} a "
                    f"{mp(max(difs))} ponto conforme a definição; positivo = os alagados andaram menos para o PL.")
    rodape(fig, extra=" · Governo do RS/SPGG, área inundada em 23/5/2024 · IBGE, Censo 2022, setores censitários")
    return salvar(fig, "numeros_4x5_4.png")


def cidades(NM):
    r = [(k, v["dentro"], v["fora"]) for k, v in NM["por_municipio"].items()
         if v["dentro"] and v["fora"] and v["dentro"]["aptos_26"] >= MIN_APTOS_CIDADE]
    return sorted(r, key=lambda x: -x[1]["aptos_26"])


def c5_cidades(NM):
    cs = cidades(NM)
    fig = cartao(5, "A mudança dentro de cada cidade",
                 "Mudança na diferença PT − PL de 2022 para 2026, em pontos percentuais, nos locais alagados e "
                 f"no resto da mesma cidade. Cidades com {mil(MIN_APTOS_CIDADE)} ou mais eleitores em locais "
                 "alagados.")
    legenda_grupos(fig, 0.05, 0.795, 11, resto="restante da mesma cidade")
    linhas = [(k, f"{mil_k(d['aptos_26'])} eleitores em locais alagados", d["mudanca_margem"], f["mudanca_margem"])
              for k, d, f in cs]
    halteres(fig, [0.05, 0.215, 0.9, 0.555], linhas, (-18, 0), [-15, -10, -5, 0], fs=11.5)
    mais = sum(d["mudanca_margem"] < f["mudanca_margem"] for _, d, f in cs)
    nota(fig, 0.175, f"Em {mais} das {len(cs)} cidades, os locais alagados andaram mais para o PL que o resto da "
                     f"cidade; nas outras {len(cs) - mais}, menos.")
    rodape(fig)
    return salvar(fig, "numeros_4x5_5.png")


def faixa_aptos(NM):
    """Menor e maior queda de aptos entre as definições de área alagada, para dentro e fora."""
    grupos = [s for _, _, s in linhas_criterios(NM)]
    return {g: (min(-s[g]["mudanca_aptos_pct"] for s in grupos), max(-s[g]["mudanca_aptos_pct"] for s in grupos))
            for g in ("dentro", "fora")}


def c6_eleitorado(NM):
    fig = cartao(6, "Eleitores aptos e comparecimento",
                 "De 2022 para 2026, só nas seções eleitorais que existem nas duas eleições. Eleitores aptos = "
                 "registrados na seção; comparecimento = quem votou ÷ aptos.")
    fig.text(0.05, 0.8, "Variação no número de eleitores aptos", fontsize=13, weight="bold", va="top")
    barras_aptos(fig, [0.05, 0.56, 0.9, 0.2], NM, fs=12.5)
    fig.text(0.05, 0.505, "Comparecimento", fontsize=13, weight="bold", va="top")
    comparecimento(fig, [0.05, 0.3, 0.9, 0.17], NM, fs=12)
    fx = faixa_aptos(NM)
    rng = lambda a, b: f"{num(a)}% e {num(b)}%"
    nota(fig, 0.225, f"Com as outras definições de área alagada do cartão 4, a queda de aptos fica entre "
                     f"{rng(*fx['dentro'])} nos locais alagados e entre {rng(*fx['fora'])} no restante. "
                     "A variação mistura quem mudou de endereço e transferiu o título, mortes, novos eleitores e "
                     "o remanejamento de eleitores entre seções pelo TSE; os dados não separam as causas.")
    rodape(fig)
    return salvar(fig, "numeros_4x5_6.png")


def c8_aptos_cidades(NM):
    cs = cidades(NM)
    fig = cartao(8, "Eleitores aptos em cada cidade",
                 "Variação no número de eleitores aptos de 2022 para 2026, em %, nos locais alagados e no resto da "
                 f"mesma cidade. Cidades com {mil(MIN_APTOS_CIDADE)} ou mais eleitores em locais alagados.")
    legenda_grupos(fig, 0.05, 0.795, 11, resto="restante da mesma cidade")
    linhas = [(k, f"{saldo(d['aptos_26'] - d['aptos_22'])} eleitores nos locais alagados",
               d["mudanca_aptos_pct"], f["mudanca_aptos_pct"]) for k, d, f in cs]
    halteres(fig, [0.05, 0.215, 0.9, 0.555], linhas, (-10, 10), [-10, -5, 0, 5, 10], fs=11.5, unidade="%")
    menos = sum(d["mudanca_aptos_pct"] < f["mudanca_aptos_pct"] for _, d, f in cs)
    nota(fig, 0.175, f"Em {menos} das {len(cs)} cidades, os locais alagados perderam mais eleitores aptos (ou "
                     "ganharam menos) que o resto da cidade.")
    rodape(fig)
    return salvar(fig, "numeros_4x5_8.png")


def c9_secoes(NM):
    lst = NM["secoes_alagadas_que_mudaram_de_local"]
    fig = cartao(9, "Seções de locais alagados que mudaram de local",
                 "Seções eleitorais que em 2022 votavam num local dentro da área alagada e em 2026 votaram em outro "
                 "local, a mais de 250 m do anterior.")
    ax = eixo_livre(fig, [0.05, 0.25, 0.9, 0.57])
    n = len(lst)
    passo = 1 / (n + 1.6)
    cols = [(0, "left", "cidade"), (0.25, "left", "local em 2022 → local em 2026"), (0.79, "right", "seções"),
            (0.905, "right", "eleitores"), (1, "right", "distância")]
    for x, ha, cab in cols:
        ax.text(x, 1, cab, ha=ha, va="top", fontsize=10.5, color=COR["texto2"])
    ax.plot([0, 1], [1 - 0.55 * passo] * 2, color=COR["limite"], lw=0.8)
    for i, s in enumerate(lst):
        y = 1 - (i + 1.15) * passo
        ax.text(0, y, s["municipio"], va="center", fontsize=11, color=COR["texto2"])
        ax.text(0.25, y + passo * 0.2, nome_curto(s["nome_2022"]), va="center", fontsize=11.5)
        ax.text(0.25, y - passo * 0.2, "→ " + nome_curto(s["nome_2026"]), va="center", fontsize=11.5, weight="bold")
        ax.text(0.79, y, str(s["secoes"]), va="center", ha="right", fontsize=11.5)
        ax.text(0.905, y, mil(s["aptos_2022"]), va="center", ha="right", fontsize=11.5)
        dist = "—" if s["distancia_m"] is None else (f"{num(s['distancia_m'] / 1000)} km" if s["distancia_m"] >= 1000
                                                    else f"{s['distancia_m']} m")
        ax.text(1, y, dist, va="center", ha="right", fontsize=11.5)
        ax.plot([0, 1], [y - passo * 0.5] * 2, color=COR["limite"], lw=0.4)
    y = 1 - (n + 1.05) * passo
    ax.text(0, y, "Total", va="center", fontsize=11.5, weight="bold")
    ax.text(0.79, y, str(sum(s["secoes"] for s in lst)), va="center", ha="right", fontsize=11.5, weight="bold")
    ax.text(0.905, y, mil(sum(s["aptos_2022"] for s in lst)), va="center", ha="right", fontsize=11.5, weight="bold")
    nota(fig, 0.225, "Eleitores = aptos dessas seções em 2022. Distância em linha reta entre os dois locais; "
                     "— = local de 2026 sem coordenada no TSE. E. E. = escola estadual; E. M. = escola municipal. "
                     "Um local que só teve a coordenada corrigida pelo TSE não entra na lista.")
    rodape(fig)
    return salvar(fig, "numeros_4x5_9.png")


# ---------- resumo 16:9 ----------

def resumo(N, NM):
    W, H = 16, 9
    fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=COR["fundo"])
    fig.text(0.025, 0.955, "Enchente de 2024 × voto para presidente na Grande Porto Alegre, em números",
             fontsize=22, weight="bold", va="top")
    fig.text(0.025, 0.903, "Locais de votação dentro da área alagada em maio de 2024 × restante da área do mapa "
                           f"({N['municipios_no_mapa']} municípios, inteiros ou em parte). 1º turno, votos válidos.",
             fontsize=12.5, color=COR["texto2"], va="top")
    xs, w = [0.025, 0.355, 0.685], 0.29
    titulos = ["1  Voto em 2026", "2  Diferença PT − PL, 2022 → 2026", "3  Eleitores aptos, 2022 → 2026"]
    for x, t in zip(xs, titulos):
        fig.text(x, 0.82, t, fontsize=14, weight="bold", va="top")
    barras_voto(fig, [xs[0], 0.4, w, 0.36], N, fs=12, altura=0.22)
    inclinacao(fig, [xs[1] + 0.02, 0.36, w - 0.01, 0.4], NM, fs=11.5)
    barras_aptos(fig, [xs[2], 0.4, w, 0.36], NM, fs=12, altura=0.22)
    d, f = N["criterios"]["ada"]["dentro"], N["criterios"]["ada"]["fora"]
    md, mf = NM["criterios"]["ada"]["dentro"], NM["criterios"]["ada"]["fora"]
    rodapes = [
        f"Em cinza, os outros candidatos. {mil(d['aptos'] / 1000)} mil eleitores votam nos {d['locais']} locais "
        f"dentro da área alagada. Diferença Lula − Flávio Bolsonaro: {mp(d['pct_lula'] - d['pct_flavio'])} nos alagados, "
        f"{mp(f['pct_lula'] - f['pct_flavio'])} no restante.",
        f"Mudança: {mp(md['mudanca_margem'])} pontos nos locais alagados e {mp(mf['mudanca_margem'])} no restante. "
        "A diferença entre os dois grupos já existia em 2022.",
        f"Só seções que existem nas duas eleições. Comparecimento: {mp(md['mudanca_comparecimento'])} pontos nos "
        f"alagados, {mp(mf['mudanca_comparecimento'])} no restante. Os dados não separam as causas (mudança de "
        "endereço, mortes, novos eleitores, remanejamento de seções).",
    ]
    for x, t in zip(xs, rodapes):
        fig.text(x, 0.27, "\n".join(textwrap.wrap(t, 60)), fontsize=11, color=COR["texto2"], va="top",
                 linespacing=1.4)
    rodape(fig, y=0.075, quebra=250, fs=8, x0=0.025, x1=0.975)
    return salvar(fig, "numeros_resumo_16x9.png")


def main():
    N = json.loads((SAIDA / "numeros.json").read_text(encoding="utf-8"))
    NM = json.loads((SAIDA / "numeros_mudanca.json").read_text(encoding="utf-8"))
    N18 = json.loads((SAIDA / "numeros_2018.json").read_text(encoding="utf-8"))
    for velho in IMG.glob("numeros_*.png"):
        velho.unlink()
    for out in [resumo(N, NM), c1_voto(N, NM), c2_mudanca(NM), c3_tres_eleicoes(N18), c4_criterios(NM),
                c5_cidades(NM), c6_eleitorado(NM), c7_antes_depois(N18), c8_aptos_cidades(NM), c9_secoes(NM)]:
        print(out)


if __name__ == "__main__":
    main()
