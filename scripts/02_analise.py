"""Cruza os locais de votação com a mancha da enchente e calcula os números.

Recorte: todo local de votação dentro do retângulo do mapa, de qualquer município. O retângulo
cobre os 12 municípios do núcleo e é esticado para não cortar ao meio as cidades das bordas.

Entradas: saida/locais_votos_2026.csv (de 01_votos.py), mancha UFRGS/IPH (ADA 6 e 8/5/2024),
mancha SPGG-RS (23/5/2024, só checagem), malha municipal IBGE 2025, setores do Censo 2022 e água
permanente da base cartográfica SEMA-RS 1:25.000.
Saídas: saida/camadas.gpkg (camadas prontas para os mapas), saida/numeros.json e
saida/peso_alagado.csv (fração alagada da população do entorno de cada ponto, usada em 05_mudanca.py)
"""
import json
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely import make_valid
from shapely.geometry import MultiPoint, Point, box

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "saida"
CRS = 31982  # SIRGAS 2000 / UTM 22S, em metros
FOLGA_M = 500
DENSIDADE_MIN = 100  # hab/km²: setores abaixo disso não são pintados na versão de áreas

NUCLEO = ["Porto Alegre", "Canoas", "Esteio", "Sapucaia do Sul", "São Leopoldo", "Novo Hamburgo",
          "Nova Santa Rita", "Eldorado do Sul", "Guaíba", "Cachoeirinha", "Gravataí", "Alvorada"]
# sedes nas bordas que o retângulo deve conter inteiras (lon, lat aproximados do centro urbano)
SEDES_BORDA = {"São Sebastião do Caí": (-51.375, -29.587), "Triunfo": (-51.718, -29.943),
               "São Jerônimo": (-51.722, -29.959)}
MARGEM_M = 3000

GPKG_UFRGS = DADOS / "ufrgs" / "cheias_rhguaiba_2024_db_v14.gpkg"
CAMADA_ADA = "analise_ada_inundacao_20240506"
CAMADA_POA_530 = "poa_inundacao_2024_530cm"
GPKG_SEMA = DADOS / "ufrgs_sema25k" / "insumos_semars_basecarto25k_rs.gpkg"
CAMADA_AGUA = "semars_trecho_massa_dagua"
GPKG_SETORES = DADOS / "ibge_setores" / "RS_setores_CD2022.gpkg"


def ler(path, layer=None, moldura=None):
    """Lê uma camada recortando pela moldura (em CRS do projeto) e devolve em CRS do projeto."""
    kw = {"layer": layer} if layer else {}
    if moldura is not None:
        crs_origem = gpd.read_file(path, rows=1, **kw).crs
        kw["bbox"] = tuple(gpd.GeoSeries([moldura], crs=CRS).to_crs(crs_origem).total_bounds)
    g = gpd.read_file(path, **kw)
    return g.to_crs(CRS)


def unir(g, moldura):
    geom = make_valid(g.geometry.values)
    return gpd.GeoSeries(geom, crs=CRS).union_all().intersection(moldura)


def chave_nome(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.upper().replace("'", "").strip()


def montar_moldura(mun_rs):
    nucleo = mun_rs[mun_rs.NM_MUN.isin(NUCLEO)]
    assert len(nucleo) == 12
    xmin, ymin, xmax, ymax = nucleo.total_bounds
    sedes = gpd.GeoSeries([Point(*c) for c in SEDES_BORDA.values()], crs=4326).to_crs(CRS)
    sx0, sy0, sx1, sy1 = sedes.total_bounds
    return box(min(xmin, sx0) - MARGEM_M, min(ymin, sy0) - MARGEM_M,
               max(xmax, sx1) + MARGEM_M, max(ymax, sy1) + MARGEM_M)


def areas_de_influencia(todos, mun_rs, municipios, agua, recorte):
    """Área em volta de cada ponto de votação (Voronoi dentro do município), por coordenada única.

    Usa todos os locais do município, mesmo fora do mapa, para a divisão ficar certa nas bordas.
    Devolve um GeoDataFrame com 'pid' (coordenada única) e a geometria da célula.
    """
    celulas = []
    for nome in municipios:
        mun = mun_rs[mun_rs.chave == chave_nome(nome)].union_all()
        p = todos[todos.municipio == nome]
        unicos = p.drop_duplicates("pid")
        if len(unicos) == 1:
            celulas.append((unicos.pid.iloc[0], mun))
            continue
        vor = shapely.voronoi_polygons(MultiPoint(list(unicos.geometry)), extend_to=mun.envelope.buffer(5000))
        cel = gpd.GeoDataFrame(geometry=list(vor.geoms), crs=CRS)
        cel = gpd.sjoin(cel, unicos[["pid", "geometry"]], predicate="contains").drop(columns="index_right")
        for pid, geom in zip(cel.pid, cel.geometry):
            celulas.append((pid, geom.intersection(mun)))
    g = gpd.GeoDataFrame({"pid": [c[0] for c in celulas]}, geometry=[c[1] for c in celulas], crs=CRS)
    g["geometry"] = g.geometry.intersection(recorte).difference(agua)
    return g[~g.is_empty]


def main():
    mun_rs = ler(f"zip://{DADOS / 'ibge_mun' / 'RS_Municipios_2025.zip'}")
    mun_rs["chave"] = mun_rs.NM_MUN.map(chave_nome)
    moldura = montar_moldura(mun_rs)
    xmin, ymin, xmax, ymax = moldura.bounds
    # as camadas de fundo vão além da moldura, para formatos que mostram um pouco mais dos lados
    recorte = box(xmin - 25000, ymin - 25000, xmax + 25000, ymax + 25000)

    agua = unir(ler(GPKG_SEMA, CAMADA_AGUA, recorte), recorte)
    ada = unir(ler(GPKG_UFRGS, CAMADA_ADA, recorte), recorte)
    spgg = unir(ler(DADOS / "spgg" / "mancha_spgg_23mai.shp", moldura=recorte), recorte)
    poa530 = unir(ler(GPKG_UFRGS, CAMADA_POA_530), recorte)
    # a mancha mostra só o que normalmente não é água
    ada_seca = ada.difference(agua)
    spgg_seca = spgg.difference(agua)
    poa530_seca = poa530.difference(agua)

    lv = pd.read_csv(SAIDA / "locais_votos_2026.csv")
    sem_coord = lv[lv.sem_coord]
    lv = lv[~lv.sem_coord]
    todos = gpd.GeoDataFrame(lv, geometry=gpd.points_from_xy(lv.lon, lv.lat), crs=4326).to_crs(CRS)
    todos["pid"] = todos.groupby(["lat", "lon"]).ngroup()
    pts = todos[todos.within(moldura)].copy()
    municipios = sorted(pts.municipio.unique())
    faltam = {chave_nome(m) for m in municipios} - set(mun_rs.chave)
    assert not faltam, faltam
    excluidos = sem_coord[sem_coord.municipio.isin(municipios)]

    pts["ada"] = pts.within(ada)
    pts["ada_500"] = pts.distance(ada) <= FOLGA_M
    pts["spgg"] = pts.within(spgg)
    pts["spgg_500"] = pts.distance(spgg) <= FOLGA_M
    # só Porto Alegre: simulação hidrostática da UFRGS para o Guaíba a 5,30 m
    pts["poa530"] = pts.within(poa530)

    # ---- versão de áreas: entorno de cada ponto de votação, só onde mora gente ----
    cel = areas_de_influencia(todos, mun_rs, municipios, agua, recorte)
    cel = cel[cel.pid.isin(pts.pid)]
    setores = ler(GPKG_SETORES, moldura=recorte)
    setores["pop"] = pd.to_numeric(setores["v0001"], errors="coerce").fillna(0)
    setores["area_t"] = setores.area
    setores = setores[setores["pop"] > 0]
    setores["dens"] = setores["pop"] / (setores.area_t / 1e6)
    pedacos = gpd.overlay(setores[["pop", "area_t", "dens", "geometry"]], cel, how="intersection",
                          keep_geom_type=True)
    pedacos["pop_p"] = pedacos["pop"] * pedacos.area / pedacos.area_t
    pedacos["pop_alag"] = pedacos["pop"] * pedacos.intersection(ada_seca).area / pedacos.area_t
    pintar = pedacos[pedacos.dens >= DENSIDADE_MIN].dissolve("pid").reset_index()[["pid", "geometry"]]
    por_ponto = pts.groupby("pid")[["lula", "flavio", "validos"]].sum()
    por_ponto["margem"] = 100 * (por_ponto.lula - por_ponto.flavio) / por_ponto.validos
    areas = pintar.merge(por_ponto.reset_index(), on="pid")

    # peso de cada ponto = fração da população do seu entorno que estava na mancha
    peso = pedacos.groupby("pid")[["pop_p", "pop_alag"]].sum()
    peso["f"] = (peso.pop_alag / peso.pop_p).clip(0, 1)
    pp = por_ponto.join(peso.f).fillna({"f": 0})
    pp[["f"]].to_csv(SAIDA / "peso_alagado.csv")

    def pond(w):
        s_l, s_f, s_v = (pp.lula * w).sum(), (pp.flavio * w).sum(), (pp.validos * w).sum()
        return {"validos_equivalentes": int(round(s_v)), "pct_lula": round(100 * s_l / s_v, 2),
                "pct_flavio": round(100 * s_f / s_v, 2)}

    def resumo(df):
        s = df[["lula", "flavio", "validos", "aptos"]].sum()
        if s.validos == 0:
            return {"locais": 0, "aptos": 0, "validos": 0, "lula": 0, "flavio": 0}
        return {
            "locais": int(len(df)), "aptos": int(s.aptos), "validos": int(s.validos),
            "lula": int(s.lula), "flavio": int(s.flavio),
            "pct_lula": round(100 * s.lula / s.validos, 2),
            "pct_flavio": round(100 * s.flavio / s.validos, 2),
        }

    def dentro_fora(df, col):
        return {"dentro": resumo(df[df[col]]), "fora": resumo(df[~df[col]])}

    poa = pts[pts.municipio == "Porto Alegre"]
    numeros = {
        "total": resumo(pts),
        "municipios_no_mapa": len(municipios),
        "criterios": {c: dentro_fora(pts, c) for c in ["ada", "ada_500", "spgg", "spgg_500"]},
        "ponderado_populacao": {"dentro": pond(pp.f), "fora": pond(1 - pp.f),
                                "pop_alagada": int(round(peso.pop_alag.sum())),
                                "pop_total": int(round(peso.pop_p.sum()))},
        "por_municipio": {m: dentro_fora(g, "ada") for m, g in pts.groupby("municipio")},
        "porto_alegre": dentro_fora(poa, "ada"),
        "porto_alegre_criterios": {c: dentro_fora(poa, c) for c in ["ada", "ada_500", "spgg", "spgg_500", "poa530"]},
        "excluidos_sem_coord": {
            "locais": int(len(excluidos)), "validos": int(excluidos.validos.sum()),
            "pct_validos": round(100 * excluidos.validos.sum() / (excluidos.validos.sum() + pts.validos.sum()), 2),
            "lista": excluidos[["municipio", "NR_ZONA", "NR_LOCAL_VOTACAO", "nome", "validos"]].to_dict("records"),
        },
        "trocam_de_lado_ada_vs_spgg": int((pts.ada != pts.spgg).sum()),
        "aptos_mapa_total": int(pts.aptos.sum() + excluidos.aptos.sum()),
        "densidade_min": DENSIDADE_MIN,
    }
    (SAIDA / "numeros.json").write_text(json.dumps(numeros, ensure_ascii=False, indent=2), encoding="utf-8")

    no_mapa = mun_rs[mun_rs.chave.isin({chave_nome(m) for m in municipios})].copy()
    vizinhos = mun_rs[mun_rs.intersects(recorte) & ~mun_rs.index.isin(no_mapa.index)].copy()
    out = SAIDA / "camadas.gpkg"
    out.unlink(missing_ok=True)
    no_mapa.to_file(out, layer="nucleo")  # municípios com locais contados
    vizinhos.to_file(out, layer="vizinhos")
    gpd.GeoDataFrame(geometry=[moldura], crs=CRS).to_file(out, layer="moldura")
    gpd.GeoDataFrame(geometry=[agua], crs=CRS).to_file(out, layer="agua")
    gpd.GeoDataFrame(geometry=[ada_seca], crs=CRS).to_file(out, layer="mancha_ufrgs")
    gpd.GeoDataFrame(geometry=[spgg_seca], crs=CRS).to_file(out, layer="mancha_spgg")
    gpd.GeoDataFrame(geometry=[poa530_seca], crs=CRS).to_file(out, layer="mancha_poa530")
    pts.to_file(out, layer="locais")
    areas.to_file(out, layer="areas")
    bairros = ler(GPKG_UFRGS, "poa_admin_bairros").rename(columns={"nmbop": "nome"})[["nome", "geometry"]]
    bairros.to_file(SAIDA / "bairros_poa.gpkg")

    print("municípios no mapa:", len(municipios), "| locais contados:", len(pts),
          "| sem coordenada (fora):", len(excluidos))
    for k, v in numeros["criterios"].items():
        d, f = v["dentro"], v["fora"]
        print(f"{k:9s} dentro: {d['locais']:4d} locais, {d['aptos']:7d} aptos | Lula {d['pct_lula']:5.2f} "
              f"Flávio {d['pct_flavio']:5.2f}  || fora: Lula {f['pct_lula']:5.2f} Flávio {f['pct_flavio']:5.2f}")
    pdz = numeros["ponderado_populacao"]
    print("ponderado pela população alagada:", pdz)
    print("trocam de lado UFRGS x SPGG:", numeros["trocam_de_lado_ada_vs_spgg"])
    print("áreas pintadas:", len(areas), "pontos | km²:", round(areas.area.sum() / 1e6, 1))


if __name__ == "__main__":
    main()
