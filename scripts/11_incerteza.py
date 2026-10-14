"""Margem de incerteza da diferença entre locais alagados e o restante, por bootstrap de zonas eleitorais.

Para cada medida, a estimativa é (mudança nos locais alagados) − (mudança no restante), com os totais somados
como nos outros números. O intervalo de 95% vem de sortear de novo, com reposição, as zonas eleitorais inteiras
(município + zona) B vezes e recalcular: locais vizinhos votam parecido, então sortear zonas inteiras dá um
intervalo mais honesto que sortear locais soltos. "Dentro das cidades" = média das diferenças de cada cidade,
pesada pelo eleitorado dos locais alagados (tira a mistura entre cidades).

Medidas: diferença PT − PL (2022 → 2026, todas as seções) e PT − PSL/PL (2018 → 2022, antes da enchente);
eleitores aptos (variação em %) e abstenção (em pontos), nos dois períodos.
Entradas: saida/camadas.gpkg, saida/mudanca.gpkg (de 05_mudanca.py), saida/tendencia_2018.csv (de
10_tendencia_2018.py). Saída: saida/numeros_incerteza.json
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

SAIDA = Path(__file__).resolve().parent.parent / "saida"
B = 2000
SEMENTE = 42


def voto(s, a, b):
    """s[..., col]: soma de (margem × válidos) e de válidos; devolve a mudança da diferença em pontos."""
    return s[..., f"num{b}"] / s[..., f"validos{b}"] - s[..., f"num{a}"] / s[..., f"validos{a}"]


def aptos(s, a, b):
    return 100 * (s[..., f"aptos{b}"] / s[..., f"aptos{a}"] - 1)


def abstencao(s, a, b):
    return 100 * (s[..., f"comp{a}"] / s[..., f"aptos{a}"] - s[..., f"comp{b}"] / s[..., f"aptos{b}"])


class Somas:
    """Somas por zona e grupo (alagado/restante), para recalcular qualquer medida a partir de pesos por zona."""

    def __init__(self, df, cols):
        self.cols = cols
        chave = df.mun.astype(str) + "-" + df.zona.astype(str)
        self.zonas = sorted(chave.unique())
        iz = chave.map({z: i for i, z in enumerate(self.zonas)}).to_numpy()
        ig = df.ada.astype(int).to_numpy()  # 0 = restante, 1 = alagado
        self.t = np.zeros((len(self.zonas), 2, len(cols)))
        np.add.at(self.t, (iz, ig), df[cols].to_numpy(float))
        mun_zona = df.groupby(chave).mun.first()
        cidades = sorted(df.mun.unique())
        self.cidade = np.array([cidades.index(mun_zona[z]) for z in self.zonas])
        self.n_cidades = len(cidades)

    def agregar(self, w):
        """w: (R, zonas) pesos → somas (R, 2, cols) e por cidade (R, cidades, 2, cols)."""
        tot = np.einsum("rz,zgc->rgc", w, self.t)
        cid = np.zeros((w.shape[0], self.n_cidades, 2, len(self.cols)))
        for c in range(self.n_cidades):
            m = self.cidade == c
            cid[:, c] = np.einsum("rz,zgc->rgc", w[:, m], self.t[m])
        return tot, cid


class Visao(dict):
    """Acesso s[..., 'col'] sobre um array cujo último eixo são as colunas."""

    def __init__(self, arr, cols):
        super().__init__()
        self.arr, self.idx = arr, {c: i for i, c in enumerate(cols)}

    def __getitem__(self, k):
        return self.arr[..., self.idx[k[-1]]]


def medir(somas, f, a, b, peso_col, w):
    tot, cid = somas.agregar(w)
    v = lambda arr: f(Visao(arr, somas.cols), a, b)
    with np.errstate(divide="ignore", invalid="ignore"):
        geral = v(tot[:, 1]) - v(tot[:, 0])
        por_cidade = v(cid[:, :, 1]) - v(cid[:, :, 0])  # (R, cidades)
        peso = cid[:, :, 1, somas.cols.index(peso_col)]
        ok = np.isfinite(por_cidade) & (peso > 0) & (cid[:, :, 0, somas.cols.index(peso_col)] > 0)
        dentro = np.nansum(np.where(ok, por_cidade * peso, 0), axis=1) / np.where(ok, peso, 0).sum(axis=1)
    return geral, dentro


def main():
    zona = (gpd.read_file(SAIDA / "camadas.gpkg", layer="locais", ignore_geometry=True)
            .groupby("pid").agg(mun=("municipio", "first"), zona=("NR_ZONA", "first")))
    m = gpd.read_file(SAIDA / "mudanca.gpkg", layer="locais", ignore_geometry=True).set_index("pid").join(zona)
    t = pd.read_csv(SAIDA / "tendencia_2018.csv")
    t["pid"] = t.pid.astype(int)
    t = t.set_index("pid").join(zona)
    for df, anos in ((m, ("22", "26")), (t, ("18", "22", "26"))):
        for a in anos:
            df[f"num{a}"] = (df[f"margem{a}"] * df[f"validos{a}"]).fillna(0)
    m = m.rename(columns={"aptos26p": "aptos26", "comp26p": "comp26"})

    sm = Somas(m, ["num22", "validos22", "num26", "validos26", "aptos22", "aptos26", "comp22", "comp26"])
    st = Somas(t, [f"{c}{a}" for a in ("18", "22") for c in ("num", "validos", "aptos", "comp")])
    rng = np.random.default_rng(SEMENTE)
    medidas = {
        "voto_22_26": (sm, voto, "22", "26", "validos22", "Diferença PT − PL, 2022 → 2026", "pontos"),
        "voto_18_22": (st, voto, "18", "22", "validos18", "Diferença PT − PSL/PL, 2018 → 2022", "pontos"),
        "aptos_22_26": (sm, aptos, "22", "26", "aptos22", "Eleitores aptos, 2022 → 2026", "%"),
        "aptos_18_22": (st, aptos, "18", "22", "aptos18", "Eleitores aptos, 2018 → 2022", "%"),
        "abstencao_22_26": (sm, abstencao, "22", "26", "aptos22", "Abstenção, 2022 → 2026", "pontos"),
        "abstencao_18_22": (st, abstencao, "18", "22", "aptos18", "Abstenção, 2018 → 2022", "pontos"),
    }
    sorteios = {}
    out = {}
    for k, (som, f, a, b, peso, rot, unid) in medidas.items():
        n = len(som.zonas)
        if n not in sorteios:
            idx = rng.integers(0, n, (B, n))
            sorteios[n] = np.stack([np.bincount(r, minlength=n) for r in idx]).astype(float)
        est_g, est_c = medir(som, f, a, b, peso, np.ones((1, n)))
        bg, bc = medir(som, f, a, b, peso, sorteios[n])
        ic = lambda x: [round(float(v), 2) for v in np.nanpercentile(x, [2.5, 97.5])]
        out[k] = {"rotulo": rot, "unidade": unid, "estimativa": round(float(est_g[0]), 2), "ic95": ic(bg),
                  "dentro_cidades": round(float(est_c[0]), 2), "ic95_cidades": ic(bc)}
        print(f"{rot:36s} {est_g[0]:+6.2f} [{out[k]['ic95'][0]:+.2f}, {out[k]['ic95'][1]:+.2f}]  dentro das cidades "
              f"{est_c[0]:+6.2f} [{out[k]['ic95_cidades'][0]:+.2f}, {out[k]['ic95_cidades'][1]:+.2f}]")
    numeros = {"medidas": out, "b": B, "semente": SEMENTE, "zonas": len(sm.zonas),
               "zonas_com_alagado": int((sm.t[:, 1, sm.cols.index("aptos22")] > 0).sum())}
    (SAIDA / "numeros_incerteza.json").write_text(json.dumps(numeros, ensure_ascii=False, indent=2), encoding="utf-8")
    print("zonas:", numeros["zonas"], "| com local alagado:", numeros["zonas_com_alagado"])


if __name__ == "__main__":
    main()
