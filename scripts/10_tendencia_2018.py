"""2018, 2022 e 2026 nas mesmas seções eleitorais, dentro e fora da área alagada.

Pergunta: as seções que alagaram em 2024 já votavam e já perdiam eleitores de um jeito diferente antes da
enchente? Para isso, a mudança de 2018 para 2022 (antes) é posta ao lado da de 2022 para 2026 (depois).

Painel equilibrado: só seções que existem nas três eleições (mesmo município, zona e número), cada uma no
ponto de votação onde funcionou em 2026 ('pid' de 02_analise.py), com a mesma classificação de alagado
dos outros números. Diferença = % do PT − % do candidato do PSL (2018) ou do PL (2022 e 2026), nos votos
válidos. Os candidatos mudam: Haddad (PT) × Jair Bolsonaro (PSL) em 2018, Lula (PT) × Jair Bolsonaro (PL)
em 2022 e Lula (PT) × Flávio Bolsonaro (PL) em 2026. Por isso o nível de cada ano não se compara com o do
outro; o que se compara é a distância entre os locais alagados e o restante, ano a ano.

Qualidade da ligação: a seção de 2018 deve ter funcionado perto de onde funcionou em 2022 e ter
eleitorado parecido; os dois testes vão no JSON.

Entradas: saida/camadas.gpkg, saida/peso_alagado.csv, saida/numeros_mudanca.json, saida/locais_votos_{2018,2022,2026}.csv e
saida/secoes_votos_{2018,2022,2026}.csv
Saídas: saida/numeros_2018.json e saida/tendencia_2018.csv (por ponto de votação)
"""
import importlib
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
M5 = importlib.import_module("05_mudanca")
SAIDA, CHAVE, SECAO, CRITERIOS = M5.SAIDA, M5.CHAVE, M5.SECAO, M5.CRITERIOS

ANOS = ("18", "22", "26")
# colunas de cada ano: (candidato do PT, candidato do PSL/PL)
CANDIDATOS = {"18": ("haddad", "bolsonaro"), "22": ("lula", "bolsonaro"), "26": ("lula", "flavio")}
CAMPOS = ["pt", "dir", "validos", "aptos", "comp", "brancos", "nulos"]
SOMAS = [f"{c}{a}" for a in ANOS for c in CAMPOS]
MESMO_LUGAR_M = 250  # a seção de 2018 funcionou a até isso do local de 2022
MIN_APTOS_CIDADE = 5000
MIN_VALIDOS = 100


def secoes(ano):
    pt, dir_ = CANDIDATOS[ano]
    s = pd.read_csv(SAIDA / f"secoes_votos_20{ano}.csv")
    s = s.rename(columns={pt: "pt", dir_: "dir", "comparecimento": "comp", "NR_LOCAL_VOTACAO": "local"})
    return s[SECAO + ["local"] + CAMPOS].rename(columns={c: f"{c}{ano}" for c in CAMPOS + ["local"]})


def resumo(df):
    s = df[SOMAS].sum()
    r = {"locais": int(len(df))} if "pid" in df or len(df) > 1 else {}
    for a in ANOS:
        v, comp, aptos = s[f"validos{a}"], s[f"comp{a}"], s[f"aptos{a}"]
        r[f"pct_pt_{a}"] = round(100 * s[f"pt{a}"] / v, 2)
        r[f"pct_dir_{a}"] = round(100 * s[f"dir{a}"] / v, 2)
        r[f"margem_{a}"] = round(r[f"pct_pt_{a}"] - r[f"pct_dir_{a}"], 2)
        r[f"aptos_{a}"] = int(aptos)
        r[f"abstencao_{a}"] = round(100 - 100 * comp / aptos, 2)
        r[f"pct_brancos_{a}"] = round(100 * s[f"brancos{a}"] / comp, 2)
        r[f"pct_nulos_{a}"] = round(100 * s[f"nulos{a}"] / comp, 2)
        r[f"validos_{a}"] = int(v)
    for a, b in (("18", "22"), ("22", "26")):
        k = f"{a}_{b}"
        for c in ("margem", "pct_pt", "pct_dir", "abstencao", "pct_brancos", "pct_nulos"):
            r[f"mudanca_{c}_{k}"] = round(r[f"{c}_{b}"] - r[f"{c}_{a}"], 2)
        r[f"mudanca_aptos_pct_{k}"] = round(100 * (s[f"aptos{b}"] / s[f"aptos{a}"] - 1), 2)
        r[f"mudanca_validos_pct_{k}"] = round(100 * (s[f"validos{b}"] / s[f"validos{a}"] - 1), 2)
    return r


def dentro_fora(df, col):
    return {"dentro": resumo(df[df[col]]), "fora": resumo(df[~df[col]])}


def ponderado(df, f):
    def grupo(w):
        r = resumo(df[SOMAS].mul(w, axis=0).sum().to_frame().T)
        r.pop("locais", None)
        return r
    return {"dentro": grupo(f), "fora": grupo(1 - f)}


def main():
    pts = gpd.read_file(SAIDA / "camadas.gpkg", layer="locais")
    cods = set(pts.CD_MUNICIPIO)
    t26 = M5.pontos(pd.read_csv(SAIDA / "locais_votos_2026.csv"))
    t26["pid"] = t26.groupby(["lat", "lon"]).ngroup()
    t26 = t26[t26.CD_MUNICIPIO.isin(cods)]
    confere = pts.merge(t26[CHAVE + ["pid"]], on=CHAVE, suffixes=("", "_r"))
    assert len(confere) == len(pts) and (confere.pid == confere.pid_r).all()

    s = {a: secoes(a) for a in ANOS}
    s = {a: d[d.CD_MUNICIPIO.isin(cods)] for a, d in s.items()}
    s["26"] = s["26"].merge(t26[CHAVE + ["pid"]].rename(columns={"NR_LOCAL_VOTACAO": "local26"}),
                            on=["CD_MUNICIPIO", "NR_ZONA", "local26"], how="left")
    s["26"] = s["26"][s["26"].pid.isin(set(pts.pid))]
    painel_s = s["26"].merge(s["22"], on=SECAO).merge(s["18"], on=SECAO)

    # ligação 2018 → 2022: a seção funcionou no mesmo lugar e tem eleitorado parecido?
    def geo(ano):
        t = M5.pontos(pd.read_csv(SAIDA / f"locais_votos_20{ano}.csv"))
        return t.set_index(CHAVE).geometry
    g18, g22 = geo("18"), geo("22")
    k18 = list(zip(painel_s.CD_MUNICIPIO, painel_s.NR_ZONA, painel_s.local18))
    k22 = list(zip(painel_s.CD_MUNICIPIO, painel_s.NR_ZONA, painel_s.local22))
    painel_s["dist_18_22"] = [g18[a].distance(g22[b]) if a in g18.index and b in g22.index else np.nan
                              for a, b in zip(k18, k22)]
    razao = painel_s.aptos22 / painel_s.aptos18
    mesmo = painel_s.dist_18_22 <= MESMO_LUGAR_M
    ligacao = {
        "secoes_2026_no_mapa": int(len(s["26"])), "secoes_nas_tres": int(len(painel_s)),
        "validos_2026_cobertos_pct": round(100 * painel_s.validos26.sum() / s["26"].validos26.sum(), 1),
        "secoes_2018_no_mapa": int(len(s["18"])),
        "mesmo_lugar_pct": round(100 * mesmo.mean(), 1),
        "mesmo_lugar_aptos_pct": round(100 * painel_s.aptos18[mesmo].sum() / painel_s.aptos18.sum(), 1),
        "sem_coordenada_pct": round(100 * painel_s.dist_18_22.isna().mean(), 1),
        "razao_aptos_mediana": round(float(razao.median()), 3),
        "razao_aptos_entre_0_7_e_1_4_pct": round(100 * razao.between(0.7, 1.4).mean(), 1),
        "mesmo_lugar_m": MESMO_LUGAR_M,
    }

    flags = pts.groupby("pid")[CRITERIOS + ["poa530"]].first().astype(bool)
    mun = pts.groupby("pid").municipio.first()
    painel = painel_s.groupby("pid")[SOMAS].sum().join(flags).join(mun)
    peso = pd.read_csv(SAIDA / "peso_alagado.csv", index_col="pid").f
    painel["f"] = peso.reindex(painel.index).fillna(0)
    so_mesmo = painel_s[mesmo].groupby("pid")[SOMAS].sum().join(flags)

    # mesmas cidades dos infográficos: pelo menos MIN_APTOS_CIDADE eleitores em locais alagados (2022 → 2026)
    NM = json.loads((SAIDA / "numeros_mudanca.json").read_text(encoding="utf-8"))
    lista = [m for m, v in NM["por_municipio"].items()
             if v["dentro"] and v["fora"] and v["dentro"]["aptos_26"] >= MIN_APTOS_CIDADE]
    cidades = {m: dentro_fora(g, "ada") for m, g in painel.groupby("municipio") if m in lista}
    assert len(cidades) == len(lista)
    numeros = {
        "total": resumo(painel),
        "criterios": {c: dentro_fora(painel, c) for c in CRITERIOS},
        "ponderado_populacao": ponderado(painel, painel.f),
        "so_secoes_no_mesmo_lugar": dentro_fora(so_mesmo, "ada"),
        "por_municipio": cidades,
        "porto_alegre": dentro_fora(painel[painel.municipio == "Porto Alegre"], "ada"),
        "ligacao": ligacao,
        "min_aptos_cidade": MIN_APTOS_CIDADE,
    }
    (SAIDA / "numeros_2018.json").write_text(json.dumps(numeros, ensure_ascii=False, indent=2), encoding="utf-8")

    por_ponto = painel[["municipio", "ada", "f"] + [f"{c}{a}" for c in ("validos", "aptos", "comp") for a in ANOS]].copy()
    for a in ANOS:
        por_ponto[f"margem{a}"] = 100 * (painel[f"pt{a}"] - painel[f"dir{a}"]) / painel[f"validos{a}"].where(
            painel[f"validos{a}"] > 0)
    por_ponto["mudanca_18_22"] = por_ponto.margem22 - por_ponto.margem18
    por_ponto["mudanca_22_26"] = por_ponto.margem26 - por_ponto.margem22
    por_ponto["comparavel"] = (painel[["validos18", "validos22", "validos26"]] >= MIN_VALIDOS).all(axis=1)
    por_ponto.round(3).to_csv(SAIDA / "tendencia_2018.csv")

    print("ligação:", ligacao)
    linhas = dict(numeros["criterios"], ponderado=numeros["ponderado_populacao"],
                  mesmo_lugar=numeros["so_secoes_no_mesmo_lugar"], POA=numeros["porto_alegre"])
    for k, v in linhas.items():
        d, f = v["dentro"], v["fora"]
        print(f"{k:12s} diferença PT−PSL/PL  dentro {d['margem_18']:+6.1f} {d['margem_22']:+6.1f} {d['margem_26']:+6.1f}"
              f" | fora {f['margem_18']:+6.1f} {f['margem_22']:+6.1f} {f['margem_26']:+6.1f}"
              f" | dentro−fora {d['margem_18'] - f['margem_18']:+5.1f} {d['margem_22'] - f['margem_22']:+5.1f}"
              f" {d['margem_26'] - f['margem_26']:+5.1f}")
        print(f"{'':12s} aptos 18→22 {d['mudanca_aptos_pct_18_22']:+5.1f}% × {f['mudanca_aptos_pct_18_22']:+5.1f}%"
              f" | 22→26 {d['mudanca_aptos_pct_22_26']:+5.1f}% × {f['mudanca_aptos_pct_22_26']:+5.1f}%"
              f" | abstenção {d['abstencao_18']:.1f} {d['abstencao_22']:.1f} {d['abstencao_26']:.1f} ×"
              f" {f['abstencao_18']:.1f} {f['abstencao_22']:.1f} {f['abstencao_26']:.1f}")
    print("por cidade (mudança da diferença 18→22 e 22→26, dentro × fora; aptos 18→22 e 22→26):")
    for m, v in cidades.items():
        d, f = v["dentro"], v["fora"]
        print(f"  {m:22s} {d['mudanca_margem_18_22']:+6.1f} × {f['mudanca_margem_18_22']:+6.1f} | "
              f"{d['mudanca_margem_22_26']:+6.1f} × {f['mudanca_margem_22_26']:+6.1f} || aptos "
              f"{d['mudanca_aptos_pct_18_22']:+5.1f} × {f['mudanca_aptos_pct_18_22']:+5.1f} | "
              f"{d['mudanca_aptos_pct_22_26']:+5.1f} × {f['mudanca_aptos_pct_22_26']:+5.1f}")


if __name__ == "__main__":
    main()
