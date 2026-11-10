"""Baixa a população dos municípios de Alagoas por ano (IBGE/SIDRA).

Estimativas anuais: tabela 6579. Censo 2022: tabela 4709, variável 93.
2023 não tem estimativa oficial e é interpolado entre 2022 e 2024.

Uso, a partir da pasta raiz do repositório:
    py src/baixar_populacao.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

PASTA = Path(__file__).resolve().parents[1] / "data" / "raw"
PASTA.mkdir(parents=True, exist_ok=True)


def sidra(url, tentativas=4):
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, timeout=120)
            resposta.raise_for_status()
            break
        except requests.RequestException:
            if tentativa == tentativas:
                raise
            time.sleep(10)  # a API do IBGE às vezes derruba a conexão
    dados = pd.DataFrame(resposta.json()[1:])  # a 1ª linha é o cabeçalho
    return pd.DataFrame({
        "geocode": dados["D1C"].astype(int),
        "ano": dados["D3N"].astype(int),
        "pop": pd.to_numeric(dados["V"], errors="coerce"),
    })


# "n6/in n3 27" = todos os municípios da UF 27 (Alagoas)
estimativas = sidra("https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2027/v/all/p/all")
censo = sidra("https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2027/v/93/p/all")
pop = pd.concat([estimativas, censo])

# 2023 não tem estimativa: média entre o Censo 2022 e a estimativa de 2024
p2022 = pop[pop["ano"] == 2022].set_index("geocode")["pop"]
p2024 = pop[pop["ano"] == 2024].set_index("geocode")["pop"]
p2023 = ((p2022 + p2024) / 2).rename("pop").reset_index().assign(ano=2023)

pop = pd.concat([pop, p2023]).sort_values(["geocode", "ano"])
pop.to_csv(PASTA / "populacao_al_ibge.csv", index=False)
print("municípios:", pop["geocode"].nunique(), "| anos:", pop["ano"].min(), "a", pop["ano"].max())
