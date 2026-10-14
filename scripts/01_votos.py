"""Votos para presidente (1º turno) por local de votação, todo o RS, em 2026, 2022 ou 2018.

Lê o CSV de votação por seção do TSE (dentro do zip, em pedaços), filtra o RS, liga cada
seção ao local onde funcionou naquela eleição (cadastro de locais de votação, com coordenada) e
soma por local. O recorte geográfico é feito depois, em 02_analise.py e 05_mudanca.py.

Uso: python -P 01_votos.py [2026|2022|2018]   (padrão 2026)
Saídas: saida/locais_votos_{ano}.csv e saida/secoes_votos_{ano}.csv (por seção, para a checagem
que segue os mesmos eleitores em 05_mudanca.py)
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "saida"
SAIDA.mkdir(exist_ok=True)

# (arquivo, membro do zip ou None se for CSV solto). n13: coluna do candidato do PT; n22 e nr: coluna e número
# do candidato do PL (Flávio em 2026, Bolsonaro em 2022) ou, em 2018, do PSL (Bolsonaro, 17)
ANOS = {
    2026: {"votos": ("tse_votos/votacao_secao_2026_BR.zip", "votacao_secao_2026_BR.csv"),
           "locais": ("tse_locais/eleitorado_local_votacao_2026_RS.csv", None),
           "n13": "lula", "n22": "flavio", "nr": 22},
    # o arquivo de 2022 por UF não traz presidente; vem do nacional
    2022: {"votos": ("tse_votos_2022/votacao_secao_2022_BR.zip", "votacao_secao_2022_BR.csv"),
           "locais": ("tse_locais_2022/eleitorado_local_votacao_2022.zip", "eleitorado_local_votacao_2022.csv"),
           "n13": "lula", "n22": "bolsonaro", "nr": 22},
    2018: {"votos": ("tse_votos_2018/votacao_secao_2018_BR.zip", "votacao_secao_2018_BR.csv"),
           "locais": ("tse_locais_2018/eleitorado_local_votacao_2018.zip", "eleitorado_local_votacao_2018.csv"),
           "n13": "haddad", "n22": "bolsonaro", "nr": 17},
}
PT = 13
NAO_VALIDOS = {95, 96, 97, 98}  # branco, nulo, anulados
BRANCO, NULOS = 95, {96, 97, 98}  # nulos = nulo + anulados
CHAVE = ["CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_municipio(s):
    """'SÃO SEBASTIÃO DO CAÍ' -> 'São Sebastião do Caí'."""
    return " ".join(p.lower() if i and p.lower() in MINUSCULAS else p.capitalize()
                    for i, p in enumerate(s.split()))


def ler_csv(arquivo, membro, filtro, **kw):
    """Lê um CSV do TSE (solto ou dentro de zip) em pedaços, ficando só com as linhas do filtro."""
    kw = dict(sep=";", encoding="latin1", chunksize=2_000_000, **kw)
    caminho = DADOS / arquivo
    if membro is None:
        return pd.concat([filtro(ch) for ch in pd.read_csv(caminho, **kw)], ignore_index=True)
    with zipfile.ZipFile(caminho) as z, z.open(membro) as f:
        return pd.concat([filtro(ch) for ch in pd.read_csv(f, **kw)], ignore_index=True)


def votos_por_secao(cfg):
    cols = ["SG_UF", "NR_TURNO", "CD_CARGO", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO",
            "NR_VOTAVEL", "QT_VOTOS"]
    return ler_csv(*cfg["votos"], lambda ch: ch[(ch.SG_UF == "RS") & (ch.NR_TURNO == 1) & (ch.CD_CARGO == 1)],
                   usecols=cols)


def locais(cfg):
    df = ler_csv(*cfg["locais"], lambda ch: ch[(ch.SG_UF == "RS") & (ch.NR_TURNO == "1")], dtype=str)
    for c in ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO", "QT_ELEITOR_SECAO"]:
        df[c] = df[c].astype(int)
    # 2026 usa vírgula decimal; 2022, ponto
    df["lat"] = df.NR_LATITUDE.str.replace(",", ".").astype(float)
    df["lon"] = df.NR_LONGITUDE.str.replace(",", ".").astype(float)
    return df


def main():
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    cfg = ANOS[ano]
    n13, n22 = cfg["n13"], cfg["n22"]
    v = votos_por_secao(cfg)
    print(ano, "linhas de voto:", len(v), "| seções:", v.groupby(["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]).ngroups)

    # O arquivo de votos traz o local "original" da seção; o cadastro de locais traz onde a
    # seção funcionou de fato (com coordenada). Usamos o local de fato, ligando por seção.
    lc = locais(cfg)
    v = v.merge(lc[["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]],
                on=["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"], how="left", validate="many_to_one")
    sem_local = v[v.NR_LOCAL_VOTACAO.isna()]
    if len(sem_local):
        print("AVISO: votos em seções fora do cadastro de locais:", int(sem_local.QT_VOTOS.sum()),
              "votos em", sem_local.groupby(["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]).ngroups, "seções")
    v = v[v.NR_LOCAL_VOTACAO.notna()].astype({"NR_LOCAL_VOTACAO": int})

    v["valido"] = ~v.NR_VOTAVEL.isin(NAO_VALIDOS)
    v[n13] = v.QT_VOTOS.where(v.NR_VOTAVEL == PT, 0)
    v[n22] = v.QT_VOTOS.where(v.NR_VOTAVEL == cfg["nr"], 0)
    v["validos"] = v.QT_VOTOS.where(v.valido, 0)
    v["brancos"] = v.QT_VOTOS.where(v.NR_VOTAVEL == BRANCO, 0)
    v["nulos"] = v.QT_VOTOS.where(v.NR_VOTAVEL.isin(NULOS), 0)
    # por seção: seções agregadas votam na urna da principal, então os aptos delas vão para a principal
    lc["SECAO_URNA"] = lc.NR_SECAO_PRINCIPAL.astype(int).where(lambda x: x > 0, lc.NR_SECAO)
    aptos_sec = (lc.groupby(["CD_MUNICIPIO", "NR_ZONA", "SECAO_URNA"]).QT_ELEITOR_SECAO.sum()
                 .rename_axis(["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]).rename("aptos"))
    sec = (v.groupby(["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"])
             [[n13, n22, "validos", "brancos", "nulos", "QT_VOTOS"]].sum()
             .rename(columns={"QT_VOTOS": "comparecimento"})
             .reset_index(level="NR_LOCAL_VOTACAO").join(aptos_sec).reset_index())
    # seção que nesta eleição funcionou fora do seu local de sempre (remanejamento só para o dia)
    lc["fora_do_original"] = ((lc.NR_LOCAL_VOTACAO != lc.NR_LOCAL_VOTACAO_ORIGINAL.astype(int))
                              | (lc.NM_LOCAL_VOTACAO != lc.NM_LOCAL_VOTACAO_ORIGINAL))
    sec = sec.merge(lc[["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "fora_do_original"]],
                    on=["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"], how="left", validate="one_to_one")
    sec.to_csv(SAIDA / f"secoes_votos_{ano}.csv", index=False)
    print("seções com voto:", len(sec), "| aptos nas seções com voto:", int(sec.aptos.sum()),
          "de", int(lc.QT_ELEITOR_SECAO.sum()))

    agg = v.groupby(CHAVE).agg(**{n13: (n13, "sum"), n22: (n22, "sum")}, validos=("validos", "sum"),
                               brancos=("brancos", "sum"), nulos=("nulos", "sum"),
                               comparecimento=("QT_VOTOS", "sum"), secoes=("NR_SECAO", "nunique")).reset_index()

    lv = (lc.groupby(CHAVE)
            .agg(municipio=("NM_MUNICIPIO", "first"), nome=("NM_LOCAL_VOTACAO", "first"),
                 bairro=("NM_BAIRRO", "first"), endereco=("DS_ENDERECO", "first"),
                 lat=("lat", "first"), lon=("lon", "first"), aptos=("QT_ELEITOR_SECAO", "sum"))
            .reset_index())
    df = agg.merge(lv, on=CHAVE, how="left", validate="one_to_one")
    df["municipio"] = df.municipio.map(nome_municipio)
    df["sem_coord"] = df.lat.isna() | (df.lat == -1) | (df.lon == -1)
    df[f"pct_{n13}"] = 100 * df[n13] / df.validos
    df[f"pct_{n22}"] = 100 * df[n22] / df.validos
    df["margem"] = df[f"pct_{n13}"] - df[f"pct_{n22}"]
    df.to_csv(SAIDA / f"locais_votos_{ano}.csv", index=False)

    print("locais no RS:", len(df), "| sem coordenada:", int(df.sem_coord.sum()),
          f"({df[df.sem_coord].validos.sum() / df.validos.sum():.2%} dos válidos)")
    tot = df[[n13, n22, "validos"]].sum()
    print("RS:", {k: f"{100 * tot[k] / tot.validos:.2f}%" for k in [n13, n22]}, "| válidos:", int(tot.validos))
    poa = df[df.CD_MUNICIPIO == 88013][[n13, n22, "validos"]].sum()
    print("conferência Porto Alegre:", poa.to_dict())


if __name__ == "__main__":
    main()
