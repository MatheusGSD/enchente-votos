"""Dados do mapa interativo (docs/, publicado no GitHub Pages).

Um ponto por local de votação (pid, a mesma unidade dos mapas), com 2018, 2022 e 2026 nas mesmas seções, e os
polígonos simplificados: mancha da UFRGS a 20 m sem pedaços menores que 1.000 m² (a área muda 0,2%), simulação
de Porto Alegre a 10 m, municípios e entornos dos locais por coverage_simplify (sem buracos entre vizinhos).
Cores, faixas e números do resumo vêm dos mesmos lugares que as figuras, para o mapa não divergir do artigo.
Extensão .json (não .geojson): é a que o Pages serve com gzip.
Lê saida/camadas.gpkg, saida/mudanca.gpkg, saida/tendencia_2018.csv e saida/numeros*.json.
Saída: docs/dados/*.json, docs/og.png e o ?v= dos arquivos em docs/index.html (rode antes de cada publicação)
"""
import hashlib
import importlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
M = importlib.import_module("03_mapas")
MM = importlib.import_module("06_mapas_mudanca")
SAIDA = M.SAIDA
WEB = M.RAIZ / "docs"
DADOS = WEB / "dados"
DADOS.mkdir(parents=True, exist_ok=True)

TOL_MANCHA, MIN_PEDACO = 20, 1000  # metros, m²
TOL_POA530, TOL_MUN, TOL_AREAS = 10, 50, 20


def gravar(gdf, nome):
    """GeoJSON em graus com 5 casas (~1 m). O arredondamento é feito aqui, antes de gravar: feito pelo GDAL, ele
    achatava polígonos estreitos em linhas e pontos."""
    out = DADOS / nome
    out.unlink(missing_ok=True)
    g = gdf.to_crs(4326)
    if (g.geom_type != "Point").all():
        g = g.set_geometry([poligonos(x) for x in shapely.set_precision(g.geometry.values, 1e-5)])
    g.to_file(out, driver="GeoJSON", COORDINATE_PRECISION=5)
    return out


def gravar_json(obj, nome):
    out = DADOS / nome
    out.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def r1(x):
    return None if pd.isna(x) else round(float(x), 1)


def poligonos(geom):
    """Só as partes de área: os recortes deixam linhas e pontos soltos em GeometryCollection, e o Leaflet
    desenha cada ponto como um marcador."""
    partes = shapely.get_parts(geom)
    while any(p.geom_type in ("GeometryCollection", "MultiPolygon") for p in partes):
        partes = np.concatenate([shapely.get_parts(p) for p in partes])
    return shapely.MultiPolygon([p for p in partes if p.geom_type == "Polygon" and not p.is_empty])


def sem_pedacos(geom, minimo):
    return shapely.MultiPolygon([p for p in poligonos(geom).geoms if p.area >= minimo])


def locais(C, T):
    """Um ponto por pid. Nomes juntos quando há mais de um local na mesma coordenada."""
    c = C[C.pid.notna()].copy()
    g = c.groupby("pid")
    base = g.agg(lula=("lula", "sum"), flavio=("flavio", "sum"), poa530=("poa530", "any"),
                 municipio=("municipio", "first"), bairro=("bairro", "first"), geometry=("geometry", "first"))
    base["nome"] = g.nome.apply(lambda s: " / ".join(dict.fromkeys(n.strip() for n in s)))
    t = T.set_index("pid")
    m = MM.carregar()[0]["m_locais"].set_index("pid")
    d = base.join(m[["validos22", "validos26", "margem22", "margem26", "mudanca", "comparavel", "ada", "f",
                     "aptos22", "aptos26p"]]).join(t[["margem18"]])
    assert len(d) == len(m), "pid sem par entre camadas.gpkg e mudanca.gpkg"
    props = pd.DataFrame({
        "pid": d.index.astype(int),
        "nome": d.nome, "mun": d.municipio, "bairro": d.bairro.fillna("").str.strip().str.title(),
        "v26": d.validos26.astype(int), "v22": d.validos22.fillna(0).astype(int),
        "lula": (100 * d.lula / d.validos26).map(r1), "flavio": (100 * d.flavio / d.validos26).map(r1),
        "m18": d.margem18.map(r1), "m22": d.margem22.map(r1), "m26": d.margem26.map(r1),
        "mud": d.mudanca.where(d.comparavel).map(r1),
        "a22": d.aptos22.fillna(0).astype(int), "a26": d.aptos26p.fillna(0).astype(int),
        "ada": d.ada.astype(bool), "f": d.f.round(2), "p530": d.poa530.astype(bool),
    }).reset_index(drop=True)
    return gpd.GeoDataFrame(props, geometry=list(d.geometry), crs=C.crs).sort_values("v26", ascending=False)


def resumo():
    """Dentro × fora da mancha, os números do artigo (mancha UFRGS, ponto dentro)."""
    N = json.loads((SAIDA / "numeros.json").read_text(encoding="utf-8"))["criterios"]["ada"]
    NM = json.loads((SAIDA / "numeros_mudanca.json").read_text(encoding="utf-8"))["criterios"]["ada"]
    N18 = json.loads((SAIDA / "numeros_2018.json").read_text(encoding="utf-8"))["criterios"]["ada"]
    NI = json.loads((SAIDA / "numeros_incerteza.json").read_text(encoding="utf-8"))["medidas"]
    r = {}
    for g in ("dentro", "fora"):
        r[g] = {"locais": N[g]["locais"], "aptos": N[g]["aptos"],
                "m26": round(N[g]["pct_lula"] - N[g]["pct_flavio"], 1),
                "m22": round(NM[g]["margem_22"], 1), "mud": round(NM[g]["mudanca_margem"], 1),
                "m18": round(N18[g]["margem_18"], 1)}
    # linha do tempo do painel: as três eleições nas seções que existem em todas (os números da figura 2 do artigo)
    r["linhas"] = {g: [round(N18[g][f"margem_{a}"], 1) for a in ("18", "22", "26")] for g in ("dentro", "fora")}
    r["ic_mud"] = NI["voto_22_26"]["ic95"]
    r["dif_mud"] = NI["voto_22_26"]["estimativa"]
    return r


def classes(cl):
    return [{"cor": cor, "rot": rot.replace("\n", " ")} for _, rot, cor in cl]


def meta():
    return {
        "gerado": date.today().isoformat(),
        "cortes": M.CORTES, "classes": classes(M.CLASSES),
        "cortes_mud": MM.CORTES_MUD, "classes_mud": classes(MM.CLASSES_MUD),
        "lados": {"26": ["Lula (PT) à frente", "Flávio Bolsonaro (PL) à frente"],
                  "22": ["Lula (PT) à frente", "Jair Bolsonaro (PL) à frente"],
                  "18": ["Haddad (PT) à frente", "Jair Bolsonaro (PSL) à frente"],
                  "mud": ["para o PT", "para o PL"]},
        "cor": M.COR,
        "fontes": {"ada": M.FONTE_ADA, "poa530": M.FONTE_530},
        "simplificacao": {"mancha_m": TOL_MANCHA, "pedaco_min_m2": MIN_PEDACO, "poa530_m": TOL_POA530,
                          "areas_m": TOL_AREAS},
    }


def carimbar():
    """Põe em index.html um ?v= com o hash de app.js e estilo.css. O Pages manda o navegador guardar os arquivos por
    10 min; com o endereço novo a cada mudança, quem já abriu o mapa não fica preso à versão antiga."""
    html = WEB / "index.html"
    t = html.read_text(encoding="utf-8")
    for nome in ("app.js", "estilo.css"):
        h = hashlib.sha1((WEB / nome).read_bytes()).hexdigest()[:8]
        t = re.sub(rf'"{re.escape(nome)}(\?v=[0-9a-f]+)?"', f'"{nome}?v={h}"', t)
    html.write_text(t, encoding="utf-8")
    return html


def og():
    """Prévia 1200 × 630 para LinkedIn e X: o centro do mapa da figura 1 do artigo."""
    src = SAIDA / "artigo" / "fig1_mapa_voto_2026.png"
    im = Image.open(src).convert("RGB")
    w, h = im.size
    alvo = 1200 / 630
    ch = int(w / alvo)
    top = int(h * 0.42 - ch / 2)
    out = WEB / "og.png"
    im.crop((0, top, w, top + ch)).resize((1200, 630), Image.LANCZOS).save(out, optimize=True)
    return out


def main():
    L = {k: gpd.read_file(SAIDA / "camadas.gpkg", layer=k) for k in ["locais", "nucleo", "mancha_ufrgs", "mancha_poa530"]}
    T = pd.read_csv(SAIDA / "tendencia_2018.csv")
    A = gpd.read_file(SAIDA / "mudanca.gpkg", layer="areas")

    pts = locais(L["locais"], T)
    print(gravar(pts, "locais.json"), len(pts))

    m = L["mancha_ufrgs"].union_all().simplify(TOL_MANCHA)
    m = sem_pedacos(m, MIN_PEDACO)
    area0 = L["mancha_ufrgs"].union_all().area
    print(f"mancha: área {100 * (m.area / area0 - 1):+.2f}%")
    print(gravar(gpd.GeoDataFrame(geometry=[m], crs=L["mancha_ufrgs"].crs), "mancha.json"))

    p = poligonos(L["mancha_poa530"].union_all().simplify(TOL_POA530))
    print(gravar(gpd.GeoDataFrame(geometry=[p], crs=L["mancha_poa530"].crs), "mancha_poa530.json"))

    n = L["nucleo"]
    geo = shapely.coverage_simplify(np.array(n.geometry), TOL_MUN)
    print(gravar(gpd.GeoDataFrame({"cd": n.CD_MUN.astype(str), "nome": n.NM_MUN}, geometry=list(geo), crs=n.crs),
                 "municipios.json"))

    geo = [poligonos(g) for g in shapely.coverage_simplify(np.array([poligonos(g) for g in A.geometry]), TOL_AREAS)]
    print(gravar(gpd.GeoDataFrame({"pid": A.pid.astype(int)}, geometry=list(geo), crs=A.crs), "areas.json"))

    print(gravar_json(resumo(), "resumo.json"))
    print(gravar_json(meta(), "meta.json"))
    print(og())
    print(carimbar())
    (WEB / ".nojekyll").touch()


if __name__ == "__main__":
    main()
