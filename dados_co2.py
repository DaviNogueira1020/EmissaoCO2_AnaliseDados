"""Leitura e preparação do dataset de CO₂ (Our World in Data / Global Carbon Project)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DATA_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
PRIMEIRO_ANO = 1750
ULTIMO_ANO = 2024  # 2025 é parcial no dataset

COLUNAS = [
    "country", "year", "iso_code", "co2", "population", "gdp", "co2_per_capita",
    "coal_co2", "oil_co2", "gas_co2", "cement_co2", "flaring_co2",
    "land_use_change_co2", "co2_including_luc", "cumulative_co2",
]
FONTES = {
    "coal_co2": "Carvão",
    "oil_co2": "Petróleo",
    "gas_co2": "Gás natural",
    "cement_co2": "Cimento",
    "flaring_co2": "Queima (flaring)",
    "land_use_change_co2": "Uso da terra",
}

# Referências geográficas (o dataset não traz continente nem blocos por país).
CONTINENTES = {
    "África": "DZA AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COG COD CIV DJI EGY GNQ ERI SWZ ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS MAR MOZ NAM NER NGA RWA STP SEN SYC SLE SOM ZAF SSD SDN TZA TGO TUN UGA ZMB ZWE ESH SHN REU MYT",
    "Ásia": "AFG ARM AZE BHR BGD BTN BRN KHM CHN GEO IND IDN IRN IRQ ISR JPN JOR KAZ KWT KGZ LAO LBN MYS MDV MNG MMR NPL PRK OMN PAK PSE PHL QAT SAU SGP KOR LKA SYR TWN TJK THA TLS TUR TKM ARE UZB VNM YEM HKG MAC",
    "Europa": "ALB AND AUT BLR BEL BIH BGR HRV CYP CZE DNK EST FRO FIN FRA DEU GIB GRC HUN ISL IRL ITA OWID_KOS LVA LIE LTU LUX MLT MDA MCO MNE NLD MKD NOR POL PRT ROU RUS SMR SRB SVK SVN ESP SWE CHE UKR GBR VAT IMN GGY JEY",
    "América do Norte": "ATG BHS BRB BLZ CAN CRI CUB DMA DOM SLV GRD GTM HTI HND JAM MEX NIC PAN KNA LCA VCT TTO USA ABW AIA BMU CYM CUW GLP GRL MTQ MSR PRI SPM SXM TCA VGB VIR BES MAF",
    "América do Sul": "ARG BOL BRA CHL COL ECU GUY PRY PER SUR URY VEN FLK GUF",
    "Oceania": "AUS FJI KIR MHL FSM NRU NZL PLW PNG WSM SLB TON TUV VUT COK NIU NCL PYF ASM GUM MNP TKL WLF PCN",
}
ISO_PARA_CONTINENTE = {
    iso: continente for continente, codigos in CONTINENTES.items() for iso in codigos.split()
}
BLOCOS = {
    "G20": set("ARG AUS BRA CAN CHN FRA DEU IND IDN ITA JPN KOR MEX RUS SAU ZAF TUR GBR USA".split()),
    "BRICS": set("BRA RUS IND CHN ZAF EGY ETH IRN ARE".split()),
    "União Europeia": set("AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE".split()),
}


@dataclass(frozen=True)
class Dados:
    """Dados já organizados: uma matriz ano × país por indicador."""

    matrizes: dict[str, pd.DataFrame]
    mundo: pd.DataFrame
    nomes: pd.Series
    continentes: pd.Series

    @cached_property
    def isos(self) -> list[str]:
        return list(self.matrizes["co2"].columns)

    @cached_property
    def nome_para_iso(self) -> dict[str, str]:
        return {nome: iso for iso, nome in self.nomes.items()}

    def soma(self, coluna: str, selecionados) -> pd.Series:
        """Soma de um indicador sobre vários países, ano a ano."""
        matriz = self.matrizes[coluna]
        selecionados = list(selecionados)
        if not selecionados:
            return pd.Series(np.nan, index=matriz.index)
        return matriz.loc[:, selecionados].sum(axis=1, min_count=1)


@lru_cache(maxsize=2)
def ler_dados(caminho_csv: str | None = None) -> Dados:
    """Lê o CSV local (se existir) ou baixa da OWID. O resultado fica em cache."""
    candidatos = [
        Path(caminho_csv) if caminho_csv else None,
        Path("owid-co2-data.csv"),
        Path("doc/owid-co2-data.csv"),
        Path("/content/owid-co2-data.csv"),
        Path("/content/doc/owid-co2-data.csv"),
    ]
    arquivo = next((p for p in candidatos if p is not None and p.is_file()), None)
    if arquivo:
        print(f"Usando dados locais: {arquivo}")
        bruto = pd.read_csv(arquivo, usecols=lambda c: c in COLUNAS)
    else:
        print("Arquivo local não encontrado; baixando o dataset da Our World in Data.")
        bruto = pd.read_csv(DATA_URL, usecols=lambda c: c in COLUNAS)

    faltantes = set(COLUNAS) - set(bruto.columns)
    if faltantes:
        raise ValueError(f"O dataset não contém as colunas necessárias: {', '.join(sorted(faltantes))}")

    bruto = bruto.loc[bruto["year"] <= ULTIMO_ANO].copy()
    bruto["year"] = bruto["year"].astype(int)
    mundo = bruto.loc[bruto["country"] == "World"].set_index("year")
    if mundo.empty or ULTIMO_ANO not in mundo.index:
        raise ValueError(f"O dataset não contém dados agregados do mundo para {ULTIMO_ANO}.")

    iso = bruto["iso_code"].astype("string")
    paises = bruto.loc[
        bruto["iso_code"].notna() & (~iso.str.startswith("OWID_", na=False) | iso.eq("OWID_KOS"))
    ].copy()  # só países: agregados (World, continentes, grupos de renda) ficam fora

    anos = range(PRIMEIRO_ANO, ULTIMO_ANO + 1)
    indicadores = [c for c in COLUNAS if c not in {"country", "iso_code", "year"}]
    matrizes = {
        coluna: paises.pivot(index="year", columns="iso_code", values=coluna).reindex(anos)
        for coluna in indicadores
    }
    info = paises.drop_duplicates("iso_code").set_index("iso_code")
    continentes = pd.Series({iso: ISO_PARA_CONTINENTE.get(iso, "Outros") for iso in info.index})
    return Dados(matrizes, mundo, info["country"], continentes)
