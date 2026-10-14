"""Gera saida/galeria.html: as versões da imagem nos dois estilos + os números de checagem."""
import json
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"

CRITERIOS = {
    "ada": "UFRGS/IPH, ponto dentro da mancha (usado nas imagens)",
    "ada_500": "UFRGS/IPH, ponto a até 500 m da mancha",
    "spgg": "Governo do RS (23/5), ponto dentro da mancha",
    "spgg_500": "Governo do RS (23/5), ponto a até 500 m da mancha",
}
MIN_APTOS_CIDADE = 5000  # mesmo corte dos infográficos por cidade
CRITERIOS_POA = dict(CRITERIOS, poa530="UFRGS/IPH, simulação hidrostática do Guaíba a 5,30 m (só Porto Alegre)")
PECAS = [
    ("triptico_16x9", "Tríptico horizontal 16:9", "1920 × 1080"),
    ("carrossel_4x5_1", "Carrossel 4:5 — slide 1", "1080 × 1350"),
    ("carrossel_4x5_2", "Carrossel 4:5 — slide 2", "1080 × 1350"),
    ("carrossel_4x5_3", "Carrossel 4:5 — slide 3", "1080 × 1350"),
    ("zoom_porto_alegre_4x5", "Zoom Porto Alegre 4:5", "1080 × 1350"),
    ("zoom_porto_alegre_4x5_simulacao530", "Zoom Porto Alegre 4:5 — simulação do Guaíba a 5,30 m", "1080 × 1350"),
]
PECAS_MUD = [
    ("triptico_16x9", "Tríptico horizontal 16:9", "1920 × 1080"),
    ("carrossel_4x5_1", "Carrossel 4:5 — slide 1 (2022)", "1080 × 1350"),
    ("carrossel_4x5_2", "Carrossel 4:5 — slide 2 (2026)", "1080 × 1350"),
    ("carrossel_4x5_3", "Carrossel 4:5 — slide 3 (mudança)", "1080 × 1350"),
    ("zoom_porto_alegre_4x5", "Zoom Porto Alegre 4:5 — mudança", "1080 × 1350"),
]
ESTILOS = [
    ("areas", "Áreas: entorno de cada local de votação, só onde mora gente",
     "Cada área é o pedaço do município mais perto de um local de votação, pintado só nos setores do Censo "
     "2022 com 100 ou mais moradores por km². A área alagada aparece hachurada."),
    ("pontos", "Pontos: um círculo por local de votação",
     "Cada círculo é um local de votação; o tamanho é o número de votos válidos. A área alagada aparece em cinza."),
]


def pct(x):
    return "—" if x is None else f"{x:.1f}".replace(".", ",") + "%"


def mil(n):
    return f"{n:,.0f}".replace(",", ".")


def pp(x):
    return "—" if x is None else f"{x:+.1f}".replace(".", ",")


def margem(s):
    return None if not s.get("validos") else s["pct_lula"] - s["pct_flavio"]


def linha(rot, d, f):
    return (f"<tr><td>{escape(rot)}</td><td class=n>{d['locais']}</td><td class=n>{mil(d['aptos'])}</td>"
            f"<td class=n>{pct(d.get('pct_lula'))}</td><td class=n>{pct(d.get('pct_flavio'))}</td>"
            f"<td class=n>{pp(margem(d))}</td><td class=n>{f['locais']}</td><td class=n>{pct(f.get('pct_lula'))}</td>"
            f"<td class=n>{pct(f.get('pct_flavio'))}</td><td class=n>{pp(margem(f))}</td></tr>")


def linha_ponderada(p):
    d, f = p["dentro"], p["fora"]
    md, mf = d["pct_lula"] - d["pct_flavio"], f["pct_lula"] - f["pct_flavio"]
    return (f"<tr><td>Ponderado pela população alagada no entorno de cada local (Censo 2022)</td>"
            f"<td class=n>—</td><td class=n>—</td><td class=n>{pct(d['pct_lula'])}</td>"
            f"<td class=n>{pct(d['pct_flavio'])}</td><td class=n>{pp(md)}</td><td class=n>—</td>"
            f"<td class=n>{pct(f['pct_lula'])}</td><td class=n>{pct(f['pct_flavio'])}</td><td class=n>{pp(mf)}</td></tr>")


def linha_mud(rot, d, f):
    if d is None or f is None:
        return ""
    loc = lambda s: s["locais"] if "locais" in s else "—"
    return (f"<tr><td>{escape(rot)}</td><td class=n>{loc(d)}</td><td class=n>{pp(d['margem_22'])}</td>"
            f"<td class=n>{pp(d['margem_26'])}</td><td class=n><b>{pp(d['mudanca_margem'])}</b></td>"
            f"<td class=n>{loc(f)}</td><td class=n>{pp(f['margem_22'])}</td><td class=n>{pp(f['margem_26'])}</td>"
            f"<td class=n><b>{pp(f['mudanca_margem'])}</b></td>"
            f"<td class=n>{pp(d['mudanca_margem'] - f['mudanca_margem'])}</td></tr>")


def linha_mud_votos(rot, s):
    return (f"<tr><td>{escape(rot)}</td><td class=n>{pct(s['pct_lula_22'])}</td><td class=n>{pct(s['pct_n22_22'])}</td>"
            f"<td class=n>{pct(s['pct_lula_26'])}</td><td class=n>{pct(s['pct_n22_26'])}</td>"
            f"<td class=n>{pp(s['mudanca_lula'])}</td><td class=n>{pp(s['mudanca_n22'])}</td></tr>")


def linha_mud_eleitorado(rot, s):
    return (f"<tr><td>{escape(rot)}</td><td class=n>{mil(s['aptos_22'])}</td><td class=n>{mil(s['aptos_26'])}</td>"
            f"<td class=n>{pp(s['mudanca_aptos_pct'])}%</td><td class=n>{pct(s['comparecimento_22'])}</td>"
            f"<td class=n>{pct(s['comparecimento_26'])}</td><td class=n>{pp(s['mudanca_comparecimento'])}</td></tr>")


def linha_abstencao(rot, s):
    tres = lambda k: (f"<td class=n>{pct(s[f'{k}_22'])}</td><td class=n>{pct(s[f'{k}_26'])}</td>"
                      f"<td class=n><b>{pp(s[f'mudanca_{k}'.replace('pct_', '')])}</b></td>")
    return f"<tr><td>{escape(rot)}</td>{tres('abstencao')}{tres('pct_brancos')}{tres('pct_nulos')}</tr>"


def linha_decomp(rot, s):
    return (f"<tr><td>{escape(rot)}</td><td class=n>{mil(s['validos_22'])}</td><td class=n>{mil(s['validos_26'])}</td>"
            f"<td class=n><b>{pp(s['mudanca_validos_pct'])}%</b></td><td class=n>{pp(s['decomp_aptos'])}</td>"
            f"<td class=n>{pp(s['decomp_comparecimento'])}</td><td class=n>{pp(s['decomp_brancos_nulos'])}</td></tr>")


def linha_abst_mun(rot, d, f):
    bn = lambda s: s["mudanca_brancos"] + s["mudanca_nulos"]
    return (f"<tr><td>{escape(rot)}</td><td class=n>{pp(d['mudanca_aptos_pct'])}%</td>"
            f"<td class=n>{pp(f['mudanca_aptos_pct'])}%</td><td class=n>{pp(d['mudanca_abstencao'])}</td>"
            f"<td class=n>{pp(f['mudanca_abstencao'])}</td><td class=n>{pp(bn(d))}</td><td class=n>{pp(bn(f))}</td></tr>")


CAB_ABST = ("<tr><th></th><th colspan=3>Abstenção (% dos aptos)</th><th colspan=3>Brancos (% de quem votou)</th>"
            "<th colspan=3>Nulos (% de quem votou)</th></tr><tr><th></th>" + "<th>2022</th><th>2026</th><th>mudança</th>" * 3
            + "</tr>")
CAB_DECOMP = ("<tr><th></th><th>válidos 2022</th><th>válidos 2026</th><th>variação</th><th>eleitores aptos</th>"
              "<th>abstenção</th><th>brancos e nulos</th></tr>")
CAB_ABST_MUN = ("<tr><th></th><th colspan=2>Aptos, variação</th><th colspan=2>Abstenção, mudança</th>"
                "<th colspan=2>Brancos + nulos, mudança</th></tr><tr><th></th>"
                + "<th>alagado</th><th>resto</th>" * 3 + "</tr>")
CAB_MUD = ("<tr><th></th><th colspan=4>Dentro da área alagada</th><th colspan=4>Fora</th><th>dentro − fora</th></tr>"
           "<tr><th></th><th>locais</th><th>margem 2022</th><th>margem 2026</th><th>mudança</th>"
           "<th>locais</th><th>margem 2022</th><th>margem 2026</th><th>mudança</th><th>mudança</th></tr>")
CAB_MUD_VOTOS = ("<tr><th></th><th>Lula (PT) 2022</th><th>Jair Bolsonaro (PL) 2022</th><th>Lula (PT) 2026</th>"
                 "<th>Flávio Bolsonaro (PL) 2026</th>"
                 "<th>PT, mudança</th><th>PL, mudança</th></tr>")
CAB_MUD_ELEIT = ("<tr><th></th><th>aptos 2022</th><th>aptos 2026</th><th>variação</th><th>comparecimento 2022</th>"
                 "<th>comparecimento 2026</th><th>mudança</th></tr>")
CAB = ("<tr><th></th><th colspan=5>Dentro da área alagada</th><th colspan=4>Fora</th></tr>"
       "<tr><th></th><th>locais</th><th>aptos</th><th>Lula (PT)</th><th>Flávio Bolsonaro (PL)</th><th>margem</th>"
       "<th>locais</th><th>Lula (PT)</th><th>Flávio Bolsonaro (PL)</th><th>margem</th></tr>")


ANOS_18 = ("18", "22", "26")
CAB_18 = ("<tr><th></th><th colspan=3>Dentro da área alagada</th><th colspan=3>Fora</th><th colspan=3>dentro − fora</th></tr>"
          "<tr><th></th>" + "<th>2018</th><th>2022</th><th>2026</th>" * 3 + "</tr>")
CAB_18_ELEIT = ("<tr><th></th><th colspan=3>Eleitores aptos</th><th colspan=2>Aptos, variação</th>"
                "<th colspan=3>Abstenção (% dos aptos)</th></tr><tr><th></th><th>2018</th><th>2022</th><th>2026</th>"
                "<th>2018 → 2022</th><th>2022 → 2026</th><th>2018</th><th>2022</th><th>2026</th></tr>")
CAB_18_MUN = ("<tr><th></th><th colspan=2>Aptos, 2018 → 2022</th><th colspan=2>Aptos, 2022 → 2026</th>"
              "<th colspan=2>Abstenção, 2018 → 2022</th><th colspan=2>Abstenção, 2022 → 2026</th></tr><tr><th></th>"
              + "<th>alagado</th><th>resto</th>" * 4 + "</tr>")


def linha_18(rot, d, f):
    cel = lambda v, b=False: f"<td class=n>{'<b>' if b else ''}{pp(v)}{'</b>' if b else ''}</td>"
    return (f"<tr><td>{escape(rot)}</td>" + "".join(cel(d[f"margem_{a}"]) for a in ANOS_18)
            + "".join(cel(f[f"margem_{a}"]) for a in ANOS_18)
            + "".join(cel(d[f"margem_{a}"] - f[f"margem_{a}"], True) for a in ANOS_18) + "</tr>")


def linha_18_eleit(rot, s):
    return (f"<tr><td>{escape(rot)}</td>" + "".join(f"<td class=n>{mil(s[f'aptos_{a}'])}</td>" for a in ANOS_18)
            + f"<td class=n>{pp(s['mudanca_aptos_pct_18_22'])}%</td><td class=n><b>{pp(s['mudanca_aptos_pct_22_26'])}%</b></td>"
            + "".join(f"<td class=n>{pct(s[f'abstencao_{a}'])}</td>" for a in ANOS_18) + "</tr>")


def linha_18_mun(rot, d, f):
    par_ = lambda k, u="": f"<td class=n>{pp(d[k])}{u}</td><td class=n>{pp(f[k])}{u}</td>"
    return (f"<tr><td>{escape(rot)}</td>{par_('mudanca_aptos_pct_18_22', '%')}{par_('mudanca_aptos_pct_22_26', '%')}"
            f"{par_('mudanca_abstencao_18_22')}{par_('mudanca_abstencao_22_26')}</tr>")


def bloco_2018():
    arq = SAIDA / "numeros_2018.json"
    if not arq.exists():
        return ""
    T = json.loads(arq.read_text(encoding="utf-8"))
    crit = "".join(linha_18(CRITERIOS[k], v["dentro"], v["fora"]) for k, v in T["criterios"].items())
    pz = T["ponderado_populacao"]
    crit += linha_18("Ponderado pela população alagada no entorno de cada local (Censo 2022)", pz["dentro"], pz["fora"])
    sm = T["so_secoes_no_mesmo_lugar"]
    crit += linha_18("UFRGS/IPH, só seções que votaram no mesmo lugar em 2018 e 2022", sm["dentro"], sm["fora"])
    ada, poa = T["criterios"]["ada"], T["porto_alegre"]
    eleit = "".join(linha_18_eleit(r, g) for r, g in [
        ("Dentro da área alagada", ada["dentro"]), ("Restante da área do mapa", ada["fora"]),
        ("Porto Alegre, dentro", poa["dentro"]), ("Porto Alegre, restante", poa["fora"])])
    mun = "".join(linha_18_mun(k, v["dentro"], v["fora"]) for k, v in
                  sorted(T["por_municipio"].items(), key=lambda kv: -kv[1]["dentro"]["aptos_26"]))
    lg = T["ligacao"]
    return f"""
<h3>Antes da enchente: 2018, 2022 e 2026 nas mesmas seções</h3>
<p class=nota>Só as seções eleitorais que existem nas três eleições (mesmo município, zona e número), cada uma no local onde
votou em 2026. Em 2018 a disputa foi Fernando Haddad (PT) × Jair Bolsonaro (PSL). Diferença = % PT − % PSL/PL nos votos
válidos. O cenário político muda de uma eleição para outra (candidatos, partidos, alianças), então o nível de um ano não se
compara com o de outro; o que se compara é a distância entre a área alagada e o restante em cada ano (últimas três colunas).</p>
<div class=scroll><table>{CAB_18}{crit}</table></div>

<h3>Eleitorado antes e depois da enchente (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Mesmas seções. De 2022 para 2026 os números diferem um pouco da tabela de eleitorado acima porque aqui entram
só as seções que já existiam em 2018.</p>
<div class=scroll><table>{CAB_18_ELEIT}{eleit}</table></div>

<h3>Eleitorado antes e depois, por cidade</h3>
<p class=nota>Cidades com {mil(T['min_aptos_cidade'])} ou mais eleitores em locais alagados. Variação dos aptos em %;
abstenção em pontos percentuais. Compare, em cada cidade, a distância entre alagado e resto antes e depois: em algumas ela
já existia antes da enchente (Canoas, por exemplo, tem a mesma distância nos dois períodos; em Guaíba e Charqueadas, os
locais alagados já perdiam eleitores antes).</p>
<div class=scroll><table>{CAB_18_MUN}{mun}</table></div>
<p class=nota>Ligação de 2018 com 2022: {mil(lg['secoes_nas_tres'])} das {mil(lg['secoes_2026_no_mapa'])} seções de 2026
nos locais do mapa existem nas três eleições ({str(lg['validos_2026_cobertos_pct']).replace('.', ',')}% dos votos válidos de
2026). Dessas, {str(lg['mesmo_lugar_pct']).replace('.', ',')}% votaram em 2018 a até {lg['mesmo_lugar_m']} m do local de 2022,
e o número de aptos de 2022 ficou entre 0,7 e 1,4 vez o de 2018 em {str(lg['razao_aptos_entre_0_7_e_1_4_pct']).replace('.', ',')}%
delas (mediana {str(lg['razao_aptos_mediana']).replace('.', ',')}): a seção de 2018 é, na prática, a mesma de 2022.</p>"""


CAB_INC = ("<tr><th></th><th>período</th><th>alagado − restante</th><th>intervalo de 95%</th>"
           "<th>dentro das cidades</th><th>intervalo de 95%</th></tr>")


def pp0(x):
    """pp() sem o "-0,0"."""
    return "0,0" if abs(x) < 0.05 else pp(x)


def intervalo(lo, hi, u):
    fora = lo > 0 or hi < 0
    t = f"{pp0(lo)}{u} a {pp0(hi)}{u}"
    return f"<b>{t}</b>" if fora else t


def bloco_incerteza():
    arq = SAIDA / "numeros_incerteza.json"
    if not arq.exists():
        return ""
    I = json.loads(arq.read_text(encoding="utf-8"))
    linhas = ""
    for nome, k in [("Diferença PT − PL (2018: PT − PSL)", "voto"), ("Eleitores aptos, variação", "aptos"),
                    ("Abstenção", "abstencao")]:
        for i, (per, rot) in enumerate([("18_22", "2018 → 2022, antes"), ("22_26", "2022 → 2026, depois")]):
            m = I["medidas"][f"{k}_{per}"]
            u = "%" if m["unidade"] == "%" else ""
            linhas += (f"<tr><td>{escape(nome) if i == 0 else ''}</td><td>{rot}</td>"
                       f"<td class=n>{pp0(m['estimativa'])}{u}</td><td class=n>{intervalo(*m['ic95'], u)}</td>"
                       f"<td class=n>{pp0(m['dentro_cidades'])}{u}</td><td class=n>{intervalo(*m['ic95_cidades'], u)}</td></tr>")
    return f"""
<h3>Margem de incerteza</h3>
<p class=nota>Quanto da diferença entre locais alagados e o restante pode ser acaso. Alagado − restante = mudança nos locais
alagados menos a mudança no restante (mancha UFRGS, ponto dentro; 2022 → 2026 com todas as seções, como nos mapas;
2018 → 2022 com as seções que existem nas três eleições). O intervalo de 95% vem de sortear de novo, com reposição, as
{I['zonas']} zonas eleitorais da área do mapa ({I['zonas_com_alagado']} com local alagado), {mil(I['b'])} vezes, e
recalcular: zonas inteiras, porque locais vizinhos votam parecido. "Dentro das cidades" compara alagado e resto em cada
cidade e tira a média, pesada pelo eleitorado alagado. Em negrito, intervalos que não incluem zero: a diferença é maior
que a margem de acaso.</p>
<div class=scroll><table>{CAB_INC}{linhas}</table></div>
<p class=nota>O intervalo mede só o acaso de quais locais e zonas existem; não cobre erros da mancha, a diferença entre
morador e local de votação nem outras diferenças entre as áreas. A perda de eleitores aptos é a única diferença que sai
da margem depois da enchente. Dentro das cidades, ela já aparecia em parte antes ({pp(I['medidas']['aptos_18_22']['dentro_cidades'])}%
de 2018 para 2022, puxada por Canoas, Eldorado do Sul e Guaíba), mas ficou maior depois
({pp(I['medidas']['aptos_22_26']['dentro_cidades'])}%).</p>"""


def figura(src, titulo, px, classe=""):
    return (f"<figure class='{classe}'><a href='{src}' target=_blank><img src='{src}' alt='{escape(titulo)}' "
            f"loading=lazy></a><figcaption><b>{escape(titulo)}</b> · {px} · <a href='{src}' download>baixar</a>"
            f"</figcaption></figure>")


def parte_mudanca():
    arq = SAIDA / "numeros_mudanca.json"
    if not arq.exists():
        return ""
    NM = json.loads(arq.read_text(encoding="utf-8"))
    secoes = ""
    for est, titulo, _ in ESTILOS:
        figs = [figura(f"imagens/mudanca_{est}_{k}.png", t, px) for k, t, px in PECAS_MUD]
        secoes += (f"<h3>{escape(titulo)}</h3><div class=wide>{figs[0]}</div><div class=grid>{''.join(figs[1:])}</div>")
    crit = "".join(linha_mud(CRITERIOS[k], v["dentro"], v["fora"]) for k, v in NM["criterios"].items())
    pz = NM["ponderado_populacao"]
    crit += linha_mud("Ponderado pela população alagada no entorno de cada local (Censo 2022)", pz["dentro"], pz["fora"])
    p22 = NM["pela_posicao_de_2022"]
    crit += linha_mud("UFRGS/IPH, cada seção pela posição do seu local em 2022 (contagem = seções)", p22["dentro"], p22["fora"])
    crit_poa = "".join(linha_mud(CRITERIOS_POA[k], v["dentro"], v["fora"])
                       for k, v in NM["porto_alegre_criterios"].items())
    com_alagado = {k: v for k, v in NM["por_municipio"].items() if v["dentro"] and v["fora"]}
    mun = "".join(linha_mud(k, v["dentro"], v["fora"]) for k, v in
                  sorted(com_alagado.items(), key=lambda kv: -kv[1]["dentro"]["aptos_26"]))
    ada = NM["criterios"]["ada"]
    grupos = [("Dentro da área alagada", ada["dentro"]), ("Restante da área do mapa", ada["fora"]),
              ("Área do mapa inteira", NM["total"])]
    votos = "".join(linha_mud_votos(r, g) for r, g in grupos)
    eleit = "".join(linha_mud_eleitorado(r, g) for r, g in grupos)
    poa = NM["porto_alegre_criterios"]["ada"]
    grupos_poa = grupos + [("Porto Alegre, dentro", poa["dentro"]), ("Porto Alegre, restante", poa["fora"])]
    abst = "".join(linha_abstencao(r, g) for r, g in grupos_poa)
    decomp = "".join(linha_decomp(r, g) for r, g in grupos_poa)
    grandes = sorted(((k, v) for k, v in com_alagado.items() if v["dentro"]["aptos_26"] >= MIN_APTOS_CIDADE),
                     key=lambda kv: -kv[1]["dentro"]["aptos_26"])
    abst_mun = "".join(linha_abst_mun(k, v["dentro"], v["fora"]) for k, v in grandes)
    lg = NM["ligacao"]
    dist = lambda m: "local de 2026 sem coordenada no TSE" if m is None else f"a {mil(m)} m"
    mudaram = "".join(f"<li>{escape(x['municipio'])}: {escape(str(x['nome_2022']))} → {escape(str(x['nome_2026']))} "
                      f"({x['secoes']} seções, {mil(x['aptos_2022'])} aptos em 2022; {dist(x['distancia_m'])})</li>"
                      for x in NM["secoes_alagadas_que_mudaram_de_local"])
    return f"""
<h2 class=parte id=parte2>2. Mudança de 2022 para 2026 nos mesmos lugares</h2>
<p class=nota>Mesma área do mapa e mesma mancha da parte 1. Em 2022 a disputa foi Lula (PT) × Jair Bolsonaro (PL); em 2026,
Lula (PT) × Flávio Bolsonaro (PL). Margem = % PT − % PL, nos votos válidos; mudança = margem de 2026 − margem de 2022.
Negativo = andou para o PL. A comparação segue as seções eleitorais: cada seção de 2022 é a mesma seção em 2026 (mesmo
município, zona e número, praticamente os mesmos eleitores) e aparece no local onde votou em 2026, que é a unidade dos mapas.
Assim a comparação não se perde quando uma escola deixou de ser local de votação ou quando o TSE corrigiu a coordenada.</p>
{secoes}

<h3>A mudança muda com o critério?</h3>
<p class=nota>A última coluna é a diferença entre a mudança dentro e a mudança fora: positiva = a área alagada andou
menos para o PL (ou mais para o PT) que o resto. Na última linha, cada seção é classificada pela posição do local onde
votava em 2022, antes da enchente, e não pelo local de 2026. A contagem de locais é por ponto de votação: locais
na mesma coordenada contam uma vez (por isso pode diferir um pouco da parte 1).</p>
<div class=scroll><table>{CAB_MUD}{crit}</table></div>

<h3>Cada candidato (mancha UFRGS, ponto dentro)</h3>
<div class=scroll><table>{CAB_MUD_VOTOS}{votos}</table></div>

<h3>Eleitorado e comparecimento (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Só seções que existem nas duas eleições. Aptos = eleitores registrados nessas seções. A variação mistura gente
que mudou de endereço e transferiu o título, mortes, novos eleitores e o remanejamento de eleitores entre seções pelo
TSE; comparecimento = votos totais ÷ aptos.</p>
<div class=scroll><table>{CAB_MUD_ELEIT}{eleit}</table></div>

<h3>Abstenção, brancos e nulos (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Mesmas seções da tabela acima. Abstenção = aptos que não votaram ÷ aptos; brancos e nulos = % de quem votou
(nulos inclui os votos anulados). Mudança em pontos percentuais.</p>
<div class=scroll><table>{CAB_ABST}{abst}</table></div>

<h3>De onde vêm os votos válidos a menos</h3>
<p class=nota>Variação dos votos válidos das mesmas seções, separada em três partes que somam a variação total (em escala
log, ×100, por isso a soma bate com a variação em % só aproximadamente): menos eleitores aptos, mais abstenção entre os
aptos e mais brancos e nulos entre quem votou. Negativo = tirou votos válidos.</p>
<div class=scroll><table>{CAB_DECOMP}{decomp}</table></div>

<h3>Eleitorado, abstenção, brancos e nulos por cidade (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Cidades com {mil(MIN_APTOS_CIDADE)} ou mais eleitores em locais alagados. Alagado = locais dentro da mancha;
resto = os outros locais da mesma cidade.</p>
<div class=scroll><table>{CAB_ABST_MUN}{abst_mun}</table></div>

<h3>Só Porto Alegre</h3>
<div class=scroll><table>{CAB_MUD}{crit_poa}</table></div>

<h3>Por município com algum local alagado (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Compara a mudança dentro e fora da mancha na mesma cidade, sem a mistura entre cidades.</p>
<div class=scroll><table>{CAB_MUD}{mun}</table></div>

<h3>Seções de locais alagados que votaram em outro lugar em 2026</h3>
<p class=nota>Seções de locais dentro da mancha em 2022 que em 2026 votaram em outro local (outro número de local, ou
remanejadas pelo TSE só para o dia da eleição) a mais de 250 m. Mesmo local com coordenada corrigida não entra.</p>
<ul>{mudaram or "<li>nenhuma</li>"}</ul>
{bloco_2018()}
{bloco_incerteza()}

<h3>Notas da parte 2</h3>
<ul>
<li>{mil(lg['secoes_2022'])} seções de 2022 nos municípios do mapa; todas existem em 2026. {lg['secoes_2022_sem_par']}
delas votaram em 2026 num local sem coordenada no TSE e ficam fora dos mapas e da tabela principal
({mil(lg['validos_2022_sem_par'])} votos válidos em 2022); entram na linha "pela posição do seu local em 2022".</li>
<li>{lg['secoes_novas_2026']} seções foram criadas em 2026 ({mil(lg['aptos_secoes_novas_2026'])} aptos): entram no voto de
2026 do local, mas não na conta de eleitorado e comparecimento. {lg['pontos_2026_sem_2022']} locais de 2026 só têm seções
novas; no mapa da mudança ficam sem cor os {lg['pontos_sem_cor']} locais sem 2022 ou com menos de {NM['min_validos']} votos
válidos em algum dos anos.</li>
<li>Os candidatos do PL são pessoas diferentes (Jair e Flávio Bolsonaro); a mudança junta o efeito do candidato, o clima nacional e o local.
Como todos os lugares passaram pela mesma troca, o que interessa é a diferença entre dentro e fora.</li>
<li>Comparação descritiva: mostra onde a votação mudou diferente, não mede efeito da enchente sobre o voto.</li>
</ul>"""


PECAS_NUM = [
    ("4x5_1", "1/9 — voto em 2026, dentro × fora"),
    ("4x5_2", "2/9 — diferença PT − PL em 2022 e 2026"),
    ("4x5_3", "3/9 — 2018, 2022 e 2026 nas mesmas seções"),
    ("4x5_4", "4/9 — a mudança com outras definições de área alagada"),
    ("4x5_5", "5/9 — a mudança dentro de cada cidade"),
    ("4x5_6", "6/9 — eleitores aptos e comparecimento"),
    ("4x5_7", "7/9 — eleitores antes e depois da enchente"),
    ("4x5_8", "8/9 — eleitores aptos em cada cidade"),
    ("4x5_9", "9/9 — seções de locais alagados que mudaram de local"),
]


PECAS_ALAG = [
    ("diptico_16x9", "Díptico 16:9 — voto em 2026 e mudança", "1920 × 1080"),
    ("voto_2026_4x5", "4:5 — voto em 2026", "1080 × 1350"),
    ("mudanca_4x5", "4:5 — mudança de 2022 para 2026", "1080 × 1350"),
]


def parte_alagados():
    if not (SAIDA / "imagens" / "alagados_pontos_diptico_16x9.png").exists():
        return ""
    secoes = ""
    for est, titulo, _ in ESTILOS:
        figs = [figura(f"imagens/alagados_{est}_{k}.png", t, px) for k, t, px in PECAS_ALAG]
        secoes += f"<h3>{escape(titulo)}</h3><div class=wide>{figs[0]}</div><div class=grid>{''.join(figs[1:])}</div>"
    return f"""
<h2 class=parte id=parte3>3. Só os locais alagados</h2>
<p class=nota>Os mesmos mapas, pintando só os locais de votação cujo ponto fica dentro da área alagada (o grupo "dentro"
dos números); os outros aparecem em contorno cinza, só para dar a referência.</p>
{secoes}"""


def parte_infograficos():
    if not (SAIDA / "imagens" / "numeros_resumo_16x9.png").exists():
        return ""
    figs = "".join(figura(f"imagens/numeros_{k}.png", t, "1080 × 1350") for k, t in PECAS_NUM)
    return f"""
<h2 class=parte id=parte4>4. Os números em infográficos</h2>
<p class=nota>Os mesmos números das partes 1 e 2, sem mapa: um resumo 16:9 e um carrossel 4:5 de 9 cartões (os
cartões 3 e 7 trazem 2018).
Mancha da UFRGS, ponto do local dentro da mancha. Em verde-azulado, os locais dentro da área alagada; em ocre, o restante.</p>
<div class=wide>{figura("imagens/numeros_resumo_16x9.png", "Resumo 16:9", "1920 × 1080")}</div>
<div class=grid>{figs}</div>"""


def main():
    N = json.loads((SAIDA / "numeros.json").read_text(encoding="utf-8"))
    secoes = ""
    for est, titulo, explica in ESTILOS:
        figs = [figura(f"imagens/{est}_{k}.png", t, px) for k, t, px in PECAS]
        secoes += (f"<h3>{escape(titulo)}</h3><p class=nota>{escape(explica)}</p>"
                   f"<div class=wide>{figs[0]}</div><div class=grid>{''.join(figs[1:])}</div>")

    crit = "".join(linha(CRITERIOS[k], v["dentro"], v["fora"]) for k, v in N["criterios"].items())
    crit += linha_ponderada(N["ponderado_populacao"])
    crit_poa = "".join(linha(CRITERIOS_POA[k], v["dentro"], v["fora"]) for k, v in N["porto_alegre_criterios"].items())
    com_alagado = {k: v for k, v in N["por_municipio"].items() if v["dentro"]["locais"] > 0}
    mun = "".join(linha(k, v["dentro"], v["fora"]) for k, v in
                  sorted(com_alagado.items(), key=lambda kv: -kv[1]["dentro"]["aptos"]))
    ex = N["excluidos_sem_coord"]
    exl = "".join(f"<li>{escape(e['municipio'])}, zona {e['NR_ZONA']}, local {e['NR_LOCAL_VOTACAO']}: "
                  f"{escape(str(e['nome']))} ({mil(e['validos'])} válidos)</li>" for e in ex["lista"])
    pz = N["ponderado_populacao"]
    mudanca = parte_mudanca()
    alagados = parte_alagados()
    infograficos = parte_infograficos()
    apres = sorted(p.name for p in SAIDA.glob("apresentacao_*.pptx"))
    link_apres = "".join(f'<a href="{a}">Apresentação ({a.removeprefix("apresentacao_").removesuffix(".pptx")}, '
                         f'PowerPoint)</a>' for a in apres)

    html = f"""<!doctype html>
<html lang=pt-BR><head><meta charset=utf-8><meta name=viewport content="width=device-width, initial-scale=1">
<title>Enchente e voto — versões</title>
<style>
:root {{ --bg:#f4f3ef; --card:#fcfcfb; --t1:#0b0b0b; --t2:#52514e; --t3:#8a8880; --line:#dedbd3; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--t1); font:15px/1.5 "Segoe UI",system-ui,sans-serif; }}
main {{ max-width:1400px; margin:0 auto; padding:28px 16px 60px; }}
h1 {{ font-size:24px; margin:0 0 4px }} h2 {{ font-size:19px; margin:40px 0 6px }}
p.sub {{ color:var(--t2); margin:0 0 8px }}
.wide figure {{ margin:0 0 18px }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:18px }}
figure {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px }}
img {{ width:100%; height:auto; display:block; border-radius:4px }}
figcaption {{ font-size:13px; color:var(--t2); margin-top:8px }}
a {{ color:#2a5d9f }}
table {{ border-collapse:collapse; background:var(--card); border:1px solid var(--line); font-size:14px; width:100% }}
th,td {{ padding:6px 10px; border-bottom:1px solid var(--line); text-align:left }}
th {{ color:var(--t2); font-weight:600 }} td.n {{ text-align:right; font-variant-numeric:tabular-nums }}
.scroll {{ overflow-x:auto }}
h2.parte {{ font-size:22px; margin:56px 0 4px; padding-top:20px; border-top:2px solid var(--t1) }}
h3 {{ font-size:17px; margin:32px 0 6px }}
nav {{ display:flex; flex-wrap:wrap; gap:8px 20px; margin:6px 0 0; font-weight:600 }}
td b {{ font-weight:700 }}
ul {{ color:var(--t2) }} .nota {{ color:var(--t2); font-size:14px; max-width:920px }}
</style></head><body><main>
<h1>Enchente de maio de 2024 e voto para presidente na Grande Porto Alegre</h1>
<p class=sub>Versões da imagem e números de checagem. Recorte: todo local de votação dentro do retângulo do mapa
({N['municipios_no_mapa']} municípios, inteiros ou em parte; {mil(N['total']['locais'])} locais). Clique numa imagem para abrir em tamanho real.</p>
<nav><a href="#parte1">1. Voto em 2026 × área alagada</a><a href="#parte2">2. Mudança de 2022 para 2026</a><a href="#parte3">3. Só os locais alagados</a><a href="#parte4">4. Infográficos</a>{link_apres}</nav>
<h2 class=parte id=parte1>1. Voto no 1º turno de 2026 × área alagada</h2>
{secoes}

<h3>O número muda com o critério?</h3>
<p class=nota>Votos válidos somados dos locais de cada grupo, na área do mapa. Margem = Lula (PT) − Flávio Bolsonaro (PL), em pontos percentuais.
{N['trocam_de_lado_ada_vs_spgg']} locais trocam de lado (dentro/fora) quando se troca a mancha da UFRGS pela do governo do RS.
Na linha ponderada, cada local entra no grupo "dentro" na proporção dos moradores do seu entorno que estavam na mancha
(cerca de {mil(pz['pop_alagada'] / 1000)} mil de {mil(pz['pop_total'] / 1000)} mil moradores).</p>
<div class=scroll><table>{CAB}{crit}</table></div>

<h3>Só Porto Alegre: o número muda com o critério?</h3>
<p class=nota>A mancha de satélite (6 e 8/5) quase não pega o Centro Histórico, a Cidade Baixa e o Menino Deus, onde a água
entrou na cidade. A simulação de 5,30 m da UFRGS é uma estimativa feita só para Porto Alegre.</p>
<div class=scroll><table>{CAB}{crit_poa}</table></div>

<h3>Por município com algum local alagado (mancha UFRGS, ponto dentro)</h3>
<p class=nota>Serve para ver se o resultado agregado vem de dentro de cada cidade ou só da mistura entre cidades.
Municípios sem nenhum local dentro da mancha ficam de fora desta tabela.</p>
<div class=scroll><table>{CAB}{mun}</table></div>

<h3>Notas da parte 1</h3>
<ul>
<li>Local de votação = onde a seção funcionou em 2026 (cadastro de locais do TSE, 1º turno).</li>
<li>Recorte: o retângulo cobre os 12 municípios do núcleo e foi esticado para conter as sedes de São Sebastião do Caí,
Triunfo e São Jerônimo. Entram todos os locais dentro dele.</li>
<li>Mancha: área diretamente afetada, UFRGS/IPH (6 e 8/5/2024), menos a água permanente da base SEMA-RS 1:25.000.
Imagens de satélite subestimam a água entre prédios; a coluna "até 500 m" dá uma ideia desse efeito.</li>
<li>Versão de áreas: o entorno de cada local é a parte do município mais perto dele do que de qualquer outro local
(calculado com todos os locais do município, inclusive os de fora do mapa), pintada só nos setores do Censo 2022 com
{N['densidade_min']} ou mais moradores por km². É uma aproximação: o TSE não diz onde mora cada eleitor.</li>
<li>{ex['locais']} locais sem coordenada no TSE ficaram de fora ({pct(ex['pct_validos'])} dos votos válidos):<ul>{exl}</ul></li>
<li>Comparação descritiva: mostra onde votou diferente, não mede efeito da enchente sobre o voto.</li>
</ul>
{mudanca}
{alagados}
{infograficos}
</main></body></html>"""
    out = SAIDA / "galeria.html"
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
