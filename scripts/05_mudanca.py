"""Mudança no voto de 2022 para 2026 nos mesmos lugares, dentro e fora da área alagada.

Ligação por seção eleitoral: cada seção de 2022 (município, zona, número) é a mesma seção em 2026,
com praticamente os mesmos eleitores, e vai para o ponto de votação onde funcionou em 2026 ('pid',
a coordenada única dos mapas). Assim a comparação segue os eleitores mesmo quando a escola mudou ou
a coordenada do TSE foi corrigida. As seções criadas em 2026 entram só no voto de 2026.

O 22 é Bolsonaro em 2022 e Flávio em 2026. Margem = % Lula − % do 22, nos votos válidos.
Eleitorado e comparecimento: só seções que existem nas duas eleições.

Entradas: saida/camadas.gpkg e saida/peso_alagado.csv (de 02_analise.py),
saida/locais_votos_{2022,2026}.csv e saida/secoes_votos_{2022,2026}.csv (de 01_votos.py)
Saídas: saida/mudanca.gpkg (camadas 'locais' e 'areas') e saida/numeros_mudanca.json
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "saida"
CRS = 31982
CRITERIOS = ["ada", "ada_500", "spgg", "spgg_500"]
CHAVE = ["CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
SECAO = ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
# 2022 e "p" = só seções que existem nas duas eleições; lula26/n22_26/validos26 = tudo o que votou no ponto em 2026
SOMAS = ["lula22", "n22_22", "validos22", "aptos22", "comp22", "brancos22", "nulos22",
         "lula26", "n22_26", "validos26", "aptos26p", "comp26p", "validos26p", "brancos26p", "nulos26p"]
PAREADAS = ["lula22", "n22_22", "validos22", "aptos22", "comp22", "brancos22", "nulos22",
            "aptos26p", "comp26p", "validos26p", "brancos26p", "nulos26p"]
MIN_VALIDOS = 100  # abaixo disso o ponto não ganha cor no mapa da mudança (ruído de local pequeno)
# seção de local alagado que em 2026 votou a mais disso do local de 2022 e em outro local (outro número,
# ou remanejada pelo TSE só para o dia) = mudou de local; mesmo número e mesmo nome = coordenada corrigida
MUDOU_M = 250


def pontos(df):
    df = df[~df.sem_coord]
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(CRS)


def resumo(df):
    s = df[SOMAS].sum()
    if s.validos22 == 0 or s.validos26 == 0:
        return None
    r = {"locais": int(len(df))}
    for a in ("22", "26"):
        r[f"pct_lula_{a}"] = round(100 * s[f"lula{a}"] / s[f"validos{a}"], 2)
        r[f"pct_n22_{a}"] = round(100 * s[f"n22_{a}"] / s[f"validos{a}"], 2)
        r[f"margem_{a}"] = round(r[f"pct_lula_{a}"] - r[f"pct_n22_{a}"], 2)
    r["aptos_22"], r["aptos_26"] = int(s.aptos22), int(s.aptos26p)
    r["comparecimento_22"] = round(100 * s.comp22 / s.aptos22, 2)
    r["comparecimento_26"] = round(100 * s.comp26p / s.aptos26p, 2)
    r["mudanca_margem"] = round(r["margem_26"] - r["margem_22"], 2)
    r["mudanca_lula"] = round(r["pct_lula_26"] - r["pct_lula_22"], 2)
    r["mudanca_n22"] = round(r["pct_n22_26"] - r["pct_n22_22"], 2)
    r["mudanca_aptos_pct"] = round(100 * (s.aptos26p / s.aptos22 - 1), 2)
    r["mudanca_comparecimento"] = round(r["comparecimento_26"] - r["comparecimento_22"], 2)
    # abstenção (% dos aptos) e brancos e nulos (% de quem votou), nas mesmas seções
    r["abstencao_22"], r["abstencao_26"] = round(100 - 100 * s.comp22 / s.aptos22, 2), round(100 - 100 * s.comp26p / s.aptos26p, 2)
    for a, comp in (("22", s.comp22), ("26", s.comp26p)):
        sufixo = a if a == "22" else "26p"
        r[f"pct_brancos_{a}"] = round(100 * s[f"brancos{sufixo}"] / comp, 2)
        r[f"pct_nulos_{a}"] = round(100 * s[f"nulos{sufixo}"] / comp, 2)
    r["mudanca_abstencao"] = round(r["abstencao_26"] - r["abstencao_22"], 2)
    r["mudanca_brancos"] = round(r["pct_brancos_26"] - r["pct_brancos_22"], 2)
    r["mudanca_nulos"] = round(r["pct_nulos_26"] - r["pct_nulos_22"], 2)
    # votos válidos das mesmas seções e de onde vem a variação (log, em %: aptos + comparecimento + válidos/votantes)
    r["validos_22"], r["validos_26"] = int(s.validos22), int(s.validos26p)
    r["mudanca_validos_pct"] = round(100 * (s.validos26p / s.validos22 - 1), 2)
    r["decomp_aptos"] = round(100 * np.log(s.aptos26p / s.aptos22), 2)
    r["decomp_comparecimento"] = round(100 * np.log((s.comp26p / s.aptos26p) / (s.comp22 / s.aptos22)), 2)
    r["decomp_brancos_nulos"] = round(100 * np.log((s.validos26p / s.comp26p) / (s.validos22 / s.comp22)), 2)
    return r


def dentro_fora(df, col):
    return {"dentro": resumo(df[df[col]]), "fora": resumo(df[~df[col]])}


def ponderado(df, f):
    """Cada ponto entra no grupo 'dentro' na proporção dos moradores do entorno que estavam na mancha."""
    def grupo(w):
        r = resumo(df[SOMAS].mul(w, axis=0).sum().to_frame().T)
        r.pop("locais")
        return r
    return {"dentro": grupo(f), "fora": grupo(1 - f)}


def main():
    pts = gpd.read_file(SAIDA / "camadas.gpkg", layer="locais")
    mancha = gpd.read_file(SAIDA / "camadas.gpkg", layer="mancha_ufrgs").union_all()
    moldura = gpd.read_file(SAIDA / "camadas.gpkg", layer="moldura").union_all()
    cods = set(pts.CD_MUNICIPIO)

    # locais de 2026 com o mesmo 'pid' de 02_analise.py
    t26 = pontos(pd.read_csv(SAIDA / "locais_votos_2026.csv"))
    t26["pid"] = t26.groupby(["lat", "lon"]).ngroup()
    t26 = t26[t26.CD_MUNICIPIO.isin(cods)]
    confere = pts.merge(t26[CHAVE + ["pid"]], on=CHAVE, suffixes=("", "_r"))
    assert len(confere) == len(pts) and (confere.pid == confere.pid_r).all()
    t22 = pontos(pd.read_csv(SAIDA / "locais_votos_2022.csv"))
    t22 = t22[t22.CD_MUNICIPIO.isin(cods)]
    t22["dentro22"] = t22.within(mancha)
    t22["no_mapa22"] = t22.within(moldura)

    # seções pareadas: 2022 → mesma seção em 2026 → ponto de 2026
    s22 = pd.read_csv(SAIDA / "secoes_votos_2022.csv")
    s26 = pd.read_csv(SAIDA / "secoes_votos_2026.csv")
    s22, s26 = s22[s22.CD_MUNICIPIO.isin(cods)], s26[s26.CD_MUNICIPIO.isin(cods)]
    s26 = s26.merge(t26[CHAVE + ["pid"]], on=CHAVE, how="left")
    ps = (s22.rename(columns={"lula": "lula22", "bolsonaro": "n22_22", "validos": "validos22", "aptos": "aptos22",
                              "comparecimento": "comp22", "brancos": "brancos22", "nulos": "nulos22",
                              "NR_LOCAL_VOTACAO": "local22"})
          .drop(columns="fora_do_original")
          .merge(s26.rename(columns={"lula": "lula26", "flavio": "n22_26", "validos": "validos26",
                                     "aptos": "aptos26p", "comparecimento": "comp26p", "brancos": "brancos26p",
                                     "nulos": "nulos26p", "NR_LOCAL_VOTACAO": "local26"}), on=SECAO, how="left"))
    ps["validos26p"] = ps.validos26  # nas seções pareadas, os válidos de 2026 são da mesma seção
    ps = ps.merge(t22[CHAVE + ["dentro22", "no_mapa22", "nome", "geometry"]]
                  .rename(columns={"NR_LOCAL_VOTACAO": "local22", "nome": "nome22", "geometry": "geo22"}),
                  on=["CD_MUNICIPIO", "NR_ZONA", "local22"], how="left")
    sem_par = ps[ps.pid.isna()]  # a seção de 2026 votou num local sem coordenada no TSE
    # checagem: cada seção pela posição do seu local em 2022, com o voto da própria seção nos dois anos
    # (não precisa da coordenada de 2026, então entram também as seções sem ponto em 2026)
    pos22 = ps[ps.local26.notna() & ps.no_mapa22.fillna(False).astype(bool)].copy()
    pos22["dentro22"] = pos22.dentro22.astype(bool)
    ps = ps[ps.pid.notna()].astype({"pid": int})

    # painel por ponto de 2026 dentro do mapa
    flags = pts.groupby("pid")[CRITERIOS + ["poa530"]].first().astype(bool)
    a26 = (pts.groupby("pid")
           .agg(municipio=("municipio", "first"), lula26=("lula", "sum"), n22_26=("flavio", "sum"),
                validos26=("validos", "sum")))
    a22 = ps.groupby("pid")[PAREADAS].sum()
    painel = a26.join(flags).join(a22).fillna({c: 0 for c in a22.columns})
    for c in a22.columns:
        painel[c] = painel[c].astype(int)
    painel["margem22"] = 100 * (painel.lula22 - painel.n22_22) / painel.validos22.where(painel.validos22 > 0)
    painel["margem26"] = 100 * (painel.lula26 - painel.n22_26) / painel.validos26
    painel["mudanca"] = painel.margem26 - painel.margem22
    painel["comparavel"] = (painel.validos22 >= MIN_VALIDOS) & (painel.validos26 >= MIN_VALIDOS)
    peso = pd.read_csv(SAIDA / "peso_alagado.csv", index_col="pid").f
    painel["f"] = peso.reindex(painel.index).fillna(0)

    # seções de locais alagados em 2022 que em 2026 votaram em outro local, longe (ou num local sem coordenada)
    geo26 = t26.drop_duplicates("pid").set_index("pid").geometry
    pos22["dist"] = [g.distance(geo26[q]) if pd.notna(q) else np.nan for g, q in zip(pos22.geo22, pos22.pid)]
    outro = (pos22.local22 != pos22.local26) | pos22.fora_do_original.fillna(False).astype(bool)
    mudou = pos22[pos22.dentro22 & outro & ~(pos22.dist <= MUDOU_M)]
    todos26 = pd.read_csv(SAIDA / "locais_votos_2026.csv").set_index(CHAVE)
    mudou = mudou.assign(
        nome26=[todos26.nome.get((m, z, int(l))) for m, z, l in zip(mudou.CD_MUNICIPIO, mudou.NR_ZONA, mudou.local26)],
        municipio=mudou.CD_MUNICIPIO.map(todos26.reset_index().drop_duplicates("CD_MUNICIPIO")
                                         .set_index("CD_MUNICIPIO").municipio))
    mudou_lista = [{"municipio": m, "nome_2022": n22, "nome_2026": n26, "secoes": int(len(g)),
                    "aptos_2022": int(g.aptos22.sum()),
                    "distancia_m": None if g.dist.isna().all() else int(round(g.dist.median()))}
                   for (m, n22, n26), g in mudou.groupby(["municipio", "nome22", "nome26"], dropna=False)]
    mudou_lista.sort(key=lambda x: -x["aptos_2022"])

    poa = painel[painel.municipio == "Porto Alegre"]
    novas = s26[s26.pid.isin(painel.index) & ~s26.set_index(SECAO).index.isin(s22.set_index(SECAO).index)]
    numeros = {
        "total": resumo(painel),
        "criterios": {c: dentro_fora(painel, c) for c in CRITERIOS},
        "ponderado_populacao": ponderado(painel, painel.f),
        "pela_posicao_de_2022": dentro_fora(pos22, "dentro22"),
        "por_municipio": {m: dentro_fora(g, "ada") for m, g in painel.groupby("municipio")},
        "porto_alegre_criterios": {c: dentro_fora(poa, c) for c in CRITERIOS + ["poa530"]},
        "ligacao": {
            "secoes_2022": int(len(s22)), "secoes_2022_sem_par": int(len(sem_par)),
            "validos_2022_sem_par": int(sem_par.validos22.sum()),
            "secoes_novas_2026": int(len(novas)), "aptos_secoes_novas_2026": int(novas.aptos.sum()),
            "pontos_2026_sem_2022": int((painel.validos22 == 0).sum()),
            "pontos_sem_cor": int((~painel.comparavel).sum()),
        },
        "secoes_alagadas_que_mudaram_de_local": mudou_lista,
        "min_validos": MIN_VALIDOS,
    }
    (SAIDA / "numeros_mudanca.json").write_text(json.dumps(numeros, ensure_ascii=False, indent=2), encoding="utf-8")

    out = SAIDA / "mudanca.gpkg"
    out.unlink(missing_ok=True)
    geo = pts.drop_duplicates("pid").set_index("pid").geometry
    cols = ["municipio", "validos22", "validos26", "margem22", "margem26", "mudanca", "comparavel", "ada", "f",
            "aptos22", "aptos26p", "comp22", "comp26p"]  # aptos e comparecimento: só seções pareadas
    loc = gpd.GeoDataFrame(painel[cols], geometry=geo.reindex(painel.index), crs=CRS).reset_index()
    loc.to_file(out, layer="locais")
    areas = gpd.read_file(SAIDA / "camadas.gpkg", layer="areas")[["pid", "geometry"]]
    areas.merge(loc.drop(columns="geometry"), on="pid").to_file(out, layer="areas")

    linhas = dict(numeros["criterios"], ponderado=numeros["ponderado_populacao"],
                  pos2022=numeros["pela_posicao_de_2022"])
    for k, v in linhas.items():
        d, f = v["dentro"], v["fora"]
        print(f"{k:9s} dentro: margem {d['margem_22']:+6.2f} -> {d['margem_26']:+6.2f} ({d['mudanca_margem']:+.2f}) "
              f"aptos {d['mudanca_aptos_pct']:+.1f}% comp {d['mudanca_comparecimento']:+.1f} || fora: margem "
              f"{f['margem_22']:+6.2f} -> {f['margem_26']:+6.2f} ({f['mudanca_margem']:+.2f}) "
              f"aptos {f['mudanca_aptos_pct']:+.1f}% comp {f['mudanca_comparecimento']:+.1f}")
        print(f"{'':9s} abstenção {d['mudanca_abstencao']:+.2f} × {f['mudanca_abstencao']:+.2f} | brancos "
              f"{d['mudanca_brancos']:+.2f} × {f['mudanca_brancos']:+.2f} | nulos {d['mudanca_nulos']:+.2f} × "
              f"{f['mudanca_nulos']:+.2f} | válidos {d['mudanca_validos_pct']:+.1f}% × {f['mudanca_validos_pct']:+.1f}%")
    print("ligação:", numeros["ligacao"])
    print("seções alagadas que mudaram de local:")
    for s in mudou_lista:
        print("  ", s)


if __name__ == "__main__":
    main()
