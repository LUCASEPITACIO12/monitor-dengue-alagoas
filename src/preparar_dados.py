"""Limpa a série de dengue, checa a qualidade e calcula a incidência anual.

Uso, a partir da pasta raiz do repositório (depois dos dois scripts de download):
    py src/preparar_dados.py
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ARQ_DENGUE = RAIZ / "data" / "raw" / "infodengue_dengue_al_2015_2025.csv"
ARQ_POP = RAIZ / "data" / "raw" / "populacao_al_ibge.csv"
TRATADOS = RAIZ / "data" / "processed"
TRATADOS.mkdir(parents=True, exist_ok=True)

dengue = pd.read_csv(ARQ_DENGUE, parse_dates=["data_iniSE"])
pop = pd.read_csv(ARQ_POP)

dengue["ano"] = dengue["SE"] // 100
dengue["semana"] = dengue["SE"] % 100
dengue = dengue.rename(columns={"pop": "pop_infodengue"})
colunas = ["geocode", "municipio", "SE", "data_iniSE", "ano", "semana",
           "casos", "casprov", "casos_est", "p_inc100k", "pop_infodengue",
           "nivel", "tempmed", "umidmed"]
dengue = dengue[colunas].sort_values(["geocode", "SE"]).reset_index(drop=True)

# Checagens de qualidade
duplicadas = int(dengue.duplicated(["geocode", "SE"]).sum())
assert duplicadas == 0, "há semanas duplicadas"
semanas = dengue.groupby("geocode").size()
intervalos = dengue.groupby("geocode")["data_iniSE"].diff().dt.days.dropna()
nulos = (dengue.isna().mean() * 100).round(1)

# Incidência anual de casos prováveis (notificados menos descartados), o critério
# dos boletins do Ministério da Saúde, com a população do IBGE de cada ano
anual = (dengue.groupby(["geocode", "municipio", "ano"], as_index=False)
         .agg(casos_notificados=("casos", "sum"), casos_provaveis=("casprov", "sum"))
         .merge(pop, on=["geocode", "ano"], how="left"))
anual["incidencia_100k"] = anual["casos_provaveis"] / anual["pop"] * 100_000

dengue.to_csv(TRATADOS / "dengue_al_semanal.csv", index=False)
anual.to_csv(TRATADOS / "dengue_al_anual.csv", index=False)


def data_do_arquivo(arquivo):
    return datetime.fromtimestamp(arquivo.stat().st_mtime).isoformat(timespec="minutes")


resumo = {
    "infodengue_baixado_em": data_do_arquivo(ARQ_DENGUE),
    "populacao_baixada_em": data_do_arquivo(ARQ_POP),
    "municipios": int(dengue["geocode"].nunique()),
    "primeira_semana": int(dengue["SE"].min()),
    "ultima_semana": int(dengue["SE"].max()),
    "semanas_por_municipio": sorted(int(n) for n in semanas.unique()),
    "buracos_na_serie": int((intervalos != 7).sum()),
    "semanas_duplicadas": duplicadas,
    "casos_negativos": int((dengue["casos"] < 0).sum()),
    "anos_sem_populacao_ibge": sorted(int(a) for a in anual.loc[anual["pop"].isna(), "ano"].unique()),
    "percentual_de_nulos": {coluna: float(valor) for coluna, valor in nulos.items() if valor > 0},
}
(TRATADOS / "resumo_qualidade.json").write_text(
    json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(resumo, ensure_ascii=False, indent=2))
