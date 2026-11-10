"""Baixa a série semanal de dengue dos 102 municípios de Alagoas no InfoDengue.

Uso, a partir da pasta raiz do repositório:
    py src/baixar_infodengue.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

ANO_INICIO, ANO_FIM = 2015, 2025
PASTA = Path(__file__).resolve().parents[1] / "data" / "raw"
PASTA.mkdir(parents=True, exist_ok=True)

# Municípios de Alagoas (código IBGE de 7 dígitos)
resp = requests.get(
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/27/municipios",
    timeout=60,
)
resp.raise_for_status()
municipios = pd.DataFrame(resp.json())[["id", "nome"]]
municipios.columns = ["geocode", "municipio"]


def baixar_infodengue(geocode, doenca="dengue"):
    url = (
        "https://info.dengue.mat.br/api/alertcity"
        f"?geocode={geocode}&disease={doenca}&format=csv"
        f"&ew_start=1&ew_end=53&ey_start={ANO_INICIO}&ey_end={ANO_FIM}"
    )
    return pd.read_csv(url)  # ler direto da URL preserva os acentos


partes, falhas = [], []
for geocode in municipios["geocode"]:
    try:
        df = baixar_infodengue(geocode)
        df["geocode"] = geocode
        partes.append(df)
    except Exception as erro:
        falhas.append((geocode, repr(erro)))
    time.sleep(0.5)  # intervalo para não sobrecarregar o servidor

dengue = pd.concat(partes, ignore_index=True).merge(municipios, on="geocode")
dengue.to_csv(PASTA / f"infodengue_dengue_al_{ANO_INICIO}_{ANO_FIM}.csv", index=False)
print("municípios:", dengue["geocode"].nunique(), "| falhas:", falhas)
if falhas:
    print("Alguns municípios falharam. Rode o script de novo.")
