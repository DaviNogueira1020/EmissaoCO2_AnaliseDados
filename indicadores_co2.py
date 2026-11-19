"""Indicadores, projeções e regras de decisão. Não depende de interface (funções puras)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from dados_co2 import ULTIMO_ANO, Dados

# Estes valores são padrões de análise do projeto, não limites definidos por uma política climática.
MIN_EMISSAO_MT = 5               # países menores que isso ficam fora do semáforo e dos grupos
HORIZONTE = 11                   # anos projetados (2025–2035)
ANOS_BACKTEST = 10               # teste: 2015–2024
JANELA_TENDENCIA = 15            # anos usados nos modelos linear e drift
CRESC_EMERGENTE = 0.03           # crescimento a.a. que define "industrialização rápida"
EMISSAO_MIN_EMERGENTE_MT = 20    # Mt mínimos para entrar no cenário de emergentes
SEMAFORO_VERDE = -1.0            # % a.a.: queda de pelo menos 1% = verde
SEMAFORO_VERMELHO = 2.0          # % a.a.: alta de 2% ou mais = vermelho
LIMIAR_CARVAO = 0.30            # recomenda trocar fontes se o carvão for 30% ou mais
LIMIAR_USO_TERRA = 0.40          # recomenda ação se uso da terra passar de 40%
MULT_PER_CAPITA_ALTO = 2.0       # alto: mais que 2 vezes a média mundial
MULT_PER_CAPITA_BAIXO = 0.5      # baixo: menos da metade da média mundial
MULT_INTENSIDADE_ALTA = 1.5      # alta: mais que 1,5 vez a intensidade mundial
PIB_MIN_BENCHMARK = 5e10         # US$: só economias relevantes entram como referência
META_REDUCAO_ANUAL = 0.01        # redução anual usada na recomendação de mobilização
ANOS_META = 10                   # duração dessa estimativa
FATOR_REFERENCIA_2030 = 0.55     # aproximação inspirada no IPCC SR1.5; não é a meta oficial aplicada diretamente.

GRUPOS = (
    "Grupo 1 – Contenção imediata",
    "Grupo 2 – Transição preventiva",
    "Grupo 3 – Redução sustentada",
    "Grupo 4 – Monitoramento",
)


# ----------------------------------------------------------------- formatação pt-BR
def br(valor, casas: int = 1, sinal: bool = False) -> str:
    """Formata número no padrão brasileiro: 1.234,5 (e +1,2 quando sinal=True)."""
    if valor is None or pd.isna(valor):
        return "–"
    texto = f"{valor:{'+' if sinal else ''},.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


# ----------------------------------------------------------------- cálculos básicos
def cagr(inicio, fim, anos: int):
    """Crescimento anual composto (aceita séries ou escalares; inválido vira NaN)."""
    if anos <= 0:
        return inicio * np.nan
    # Converte a mudança total em uma taxa anual equivalente.
    resultado = (fim / inicio) ** (1 / anos) - 1
    if isinstance(resultado, pd.Series):
        return resultado.where((inicio > 0) & (fim > 0))
    return resultado if (inicio > 0 and fim > 0) else np.nan


def ano_pib(matrizes: dict, fim: int) -> int:
    """Último ano até `fim` com PIB disponível para a maioria dos países (o PIB termina em 2022)."""
    contagem = matrizes["gdp"].loc[:fim].notna().sum(axis=1)
    suficiente = contagem[contagem >= 0.5 * contagem.max()]
    return int(suficiente.index.max()) if not suficiente.empty else fim


def economia_acumulada(emissao_anual: float, taxa: float = META_REDUCAO_ANUAL, anos: int = ANOS_META) -> float:
    """CO₂ evitado, somado ano a ano, ao reduzir `taxa` ao ano frente à emissão atual constante."""
    return emissao_anual * sum(1 - (1 - taxa) ** ano for ano in range(1, anos + 1))


# ----------------------------------------------------------------- projeção
@dataclass(frozen=True)
class Previsao:
    modelo: str
    mape: float
    projecao: np.ndarray
    banda: np.ndarray


def prever(serie: pd.Series, horizonte: int = HORIZONTE) -> Previsao | None:
    """Escolhe o modelo pelo menor erro no backtest (2015–2024) e projeta `horizonte` anos."""
    historico = serie.dropna().loc[1950:ULTIMO_ANO]
    if len(historico) < 40 or historico.index[-1] != ULTIMO_ANO:
        return None
    y = historico.to_numpy(dtype=float)
    n = JANELA_TENDENCIA

    def linear(amostra, passos):
        x = np.arange(len(amostra))[-n:]
        return np.polyval(np.polyfit(x, amostra[-n:], 1), np.arange(len(amostra), len(amostra) + passos))

    def drift(amostra, passos):
        return amostra[-1] + (amostra[-1] - amostra[-1 - n]) / n * np.arange(1, passos + 1)

    def holt(amostra, passos):
        return ExponentialSmoothing(amostra, trend="add", damped_trend=True).fit().forecast(passos)

    # Guardamos os últimos dez anos para testar cada modelo antes de projetar.
    modelos = {"Tendência linear (15 anos)": linear, "Drift (15 anos)": drift, "Holt amortecido": holt}
    teste = y[-ANOS_BACKTEST:]
    resultados = {}
    for nome, modelo in modelos.items():
        try:
            erro = np.asarray(modelo(y[:-ANOS_BACKTEST], ANOS_BACKTEST)) - teste
        except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as exc:
            warnings.warn(f"Modelo '{nome}' ignorado no backtest: {exc}")
            continue
        resultados[nome] = (float(np.mean(np.abs(erro) / np.abs(teste)) * 100), float(np.sqrt(np.mean(erro**2))))
    if not resultados:
        return None
    melhor = min(resultados, key=lambda nome: resultados[nome][0])
    mape, rmse = resultados[melhor]
    # Faixa heurística baseada no erro do teste; não é um intervalo de confiança formal.
    banda = 1.28 * rmse * np.sqrt(np.arange(1, horizonte + 1) / 5)
    return Previsao(melhor, mape, np.asarray(modelos[melhor](y, horizonte)), banda)


@dataclass(frozen=True)
class Cenario:
    anos: np.ndarray
    historico: pd.Series
    base: pd.Series
    cenario: pd.Series
    referencia_2030: float
    top5: list
    n_emergentes: int


def simular_cenario(dados: Dados, reducao: float, troca: float, janela: int) -> Cenario:
    """What-if: os 5 maiores emissores reduzem `reducao`% ao ano e os países em industrialização
    rápida trocam `troca`% do carvão por energia limpa até 2035. Resultado em Gt."""
    co2, carvao = dados.matrizes["co2"], dados.matrizes["coal_co2"]
    anos = np.arange(ULTIMO_ANO + 1, ULTIMO_ANO + 1 + HORIZONTE)
    hist = co2.loc[ULTIMO_ANO - 10:ULTIMO_ANO]
    x = np.arange(len(hist))
    # A linha de base prolonga a tendência linear observada nos últimos dez anos.
    inclinacao = hist.apply(
        lambda col: np.polyfit(x[col.notna().values], col.dropna().values, 1)[0] if col.notna().sum() >= 6 else np.nan
    )
    validos = inclinacao.dropna().index
    base = pd.DataFrame(
        {iso: np.maximum(co2.loc[ULTIMO_ANO, iso] + inclinacao[iso] * (anos - ULTIMO_ANO), 0) for iso in validos},
        index=anos,
    )
    # Os cinco maiores seguem a redução anual; os demais elegíveis são tratados como emergentes.
    top5 = list(co2.loc[ULTIMO_ANO, validos].nlargest(5).index)
    crescimento = cagr(co2.loc[ULTIMO_ANO - janela, validos], co2.loc[ULTIMO_ANO, validos], janela)
    emergentes = [
        iso for iso in validos
        if iso not in top5 and crescimento.get(iso, np.nan) >= CRESC_EMERGENTE
        and co2.loc[ULTIMO_ANO, iso] >= EMISSAO_MIN_EMERGENTE_MT
    ]
    cenario = base.copy()
    for iso in top5:
        cenario[iso] = base[iso] * (1 - reducao / 100) ** (anos - ULTIMO_ANO)
    # A troca de carvão cresce gradualmente até 2035 e respeita a participação do carvão no país.
    for iso in emergentes:
        peso_carvao = np.clip(carvao.loc[ULTIMO_ANO, iso] / co2.loc[ULTIMO_ANO, iso], 0, 1)
        cenario[iso] = base[iso] * (1 - troca / 100 * (anos - ULTIMO_ANO) / HORIZONTE * peso_carvao)
    historico = co2[validos].loc[2000:ULTIMO_ANO].sum(axis=1) / 1000
    referencia = FATOR_REFERENCIA_2030 * co2.loc[2010, validos].sum() / 1000
    return Cenario(anos, historico, base.sum(axis=1) / 1000, cenario.sum(axis=1) / 1000, referencia, top5, len(emergentes))


# ----------------------------------------------------------------- tabelas de análise
def tabela_aceleracao(dados: Dados, permitidos: list, fim: int, janela: int) -> pd.DataFrame:
    """Para cada país: emissão no início e no fim da janela, multiplicador e participação mundial."""
    co2, mundo = dados.matrizes["co2"], dados.mundo["co2"]
    ini = fim - janela
    inicio, final = co2.loc[ini, permitidos], co2.loc[fim, permitidos]
    return pd.DataFrame({
        "País": [dados.nomes[i] for i in permitidos],
        "CO₂ início (Mt)": inicio.values,
        "CO₂ fim (Mt)": final.values,
        "Multiplicador": (final / inicio).values,
        "Participação inicial (%)": (inicio / mundo.get(ini, np.nan) * 100).values,
        "Participação atual (%)": (final / mundo.get(fim, np.nan) * 100).values,
        "Crescimento a.a. (%)": (cagr(inicio, final, janela) * 100).values,
    })


def classificar_grupos(dados: Dados, permitidos: list, fim: int, janela: int,
                       volume: float, crescimento_alto: float) -> pd.DataFrame:
    """Matriz de priorização: volume de emissão × velocidade de crescimento."""
    co2 = dados.matrizes["co2"]
    final = co2.loc[fim, permitidos]
    tabela = pd.DataFrame({
        "País": [dados.nomes[i] for i in permitidos],
        "CO₂ (Mt)": final.values,
        "Crescimento a.a. (%)": (cagr(co2.loc[fim - janela, permitidos], final, janela) * 100).values,
    }).dropna()
    tabela = tabela[tabela["CO₂ (Mt)"] >= MIN_EMISSAO_MT].copy()
    tabela["Participação (%)"] = tabela["CO₂ (Mt)"] / dados.mundo["co2"].get(fim, np.nan) * 100
    alto_volume = tabela["Participação (%)"] >= volume
    alto_cresc = tabela["Crescimento a.a. (%)"] >= crescimento_alto
    # Volume e crescimento combinados definem a prioridade de cada país.
    tabela["Grupo"] = np.select(
        [alto_volume & alto_cresc, ~alto_volume & alto_cresc, alto_volume & ~alto_cresc], GRUPOS[:3], GRUPOS[3]
    )
    return tabela


def semaforo(dados: Dados, permitidos: list, fim: int, janela: int, limite: int = 30) -> pd.DataFrame:
    """Status por país: verde (queda real), amarelo (estável) ou vermelho (acelerando)."""
    co2 = dados.matrizes["co2"]
    final = co2.loc[fim, permitidos]
    tabela = pd.DataFrame({
        "País": [dados.nomes[i] for i in permitidos],
        "CO₂ (Mt)": final.values,
        "Crescimento a.a. (%)": (cagr(co2.loc[fim - janela, permitidos], final, janela) * 100).values,
    }).dropna()
    tabela = tabela[tabela["CO₂ (Mt)"] >= MIN_EMISSAO_MT].copy()
    # Queda de pelo menos 1% é verde; alta de 2% ou mais é vermelha.
    tabela["Status"] = np.select(
        [tabela["Crescimento a.a. (%)"] <= SEMAFORO_VERDE, tabela["Crescimento a.a. (%)"] >= SEMAFORO_VERMELHO],
        ["Verde", "Vermelho"], "Amarelo",
    )
    return tabela.sort_values("CO₂ (Mt)", ascending=False).head(limite)


def benchmark(dados: Dados, alvo: list, ano: int, janela: int, n: int = 3) -> pd.DataFrame:
    """Economias de renda parecida que cresceram o PIB e reduziram o CO₂ na janela."""
    m = dados.matrizes
    candidatos = pd.DataFrame({
        "País": [dados.nomes[i] for i in dados.isos],
        "PIB (%)": ((m["gdp"].loc[ano] / m["gdp"].loc[ano - janela] - 1) * 100).values,
        "CO₂ (%)": ((m["co2"].loc[ano] / m["co2"].loc[ano - janela] - 1) * 100).values,
        "PIB per capita": (m["gdp"].loc[ano] / m["population"].loc[ano]).values,
        "CO₂ per capita": m["co2_per_capita"].loc[ano].values,
        "PIB": m["gdp"].loc[ano].values,
    }).replace([np.inf, -np.inf], np.nan).dropna()
    candidatos = candidatos[
        (candidatos["PIB (%)"] > 0) & (candidatos["CO₂ (%)"] < 0) & (candidatos["PIB"] > PIB_MIN_BENCHMARK)
        & (candidatos["PIB per capita"] > 0) & ~candidatos["País"].isin([dados.nomes[i] for i in alvo])
    ].copy()
    pib_pc_alvo = dados.soma("gdp", alvo).get(ano, np.nan) / dados.soma("population", alvo).get(ano, np.nan)
    if candidatos.empty or not np.isfinite(pib_pc_alvo) or pib_pc_alvo <= 0:
        return candidatos.iloc[0:0]
    # A distância logarítmica compara rendas relativas, não a diferença bruta em dólares.
    candidatos["Distância de renda"] = np.abs(np.log(candidatos["PIB per capita"] / pib_pc_alvo))
    return candidatos.nsmallest(n, "Distância de renda").drop(columns=["PIB", "Distância de renda"])


# ----------------------------------------------------------------- recomendações
@dataclass(frozen=True)
class Recomendacao:
    titulo: str
    texto: str
    nivel: str  # "alerta" | "atencao" | "info" | "ok" (define a cor do cartão)


def recomendar(dados: Dados, alvo: list, nome_alvo: str, fim: int, janela: int,
               volume: float, crescimento_alto: float) -> list[Recomendacao]:
    """Regras de decisão baseadas nos indicadores do escopo analisado."""
    co2 = dados.soma("co2", alvo)
    emissao_ini, emissao_fim = co2.get(fim - janela, np.nan), co2.get(fim, np.nan)
    total_mundo = dados.mundo["co2"].get(fim, np.nan)
    cresc = cagr(emissao_ini, emissao_fim, janela) if emissao_ini > 0 and emissao_fim > 0 else np.nan
    part = emissao_fim / total_mundo * 100 if total_mundo > 0 else np.nan
    recs: list[Recomendacao] = []

    if pd.notna(cresc) and pd.notna(part):
        c = cresc * 100
        if part >= volume and c >= crescimento_alto:
            recs.append(Recomendacao("Contenção imediata — prioridade máxima",
                f"**{nome_alvo}** respondeu por {br(part)}% das emissões globais e cresce {br(c, 1, True)}% ao ano. "
                "Sem antecipar o pico, o impacto climático e o custo regulatório tendem a aumentar.", "alerta"))
        elif part < volume and c >= crescimento_alto:
            recs.append(Recomendacao("Decisão preventiva",
                f"O crescimento de {br(c, 1, True)}% ao ano ocorre com {br(part)}% das emissões mundiais. "
                "Investir agora em infraestrutura limpa evita uma dependência fóssil difícil de corrigir.", "atencao"))
        elif part >= volume:
            recs.append(Recomendacao("Redução sustentada",
                f"**{nome_alvo}** representa {br(part)}% das emissões globais, com variação de {br(c, 1, True)}% ao ano. "
                "A prioridade é preservar e acelerar a queda com metas absolutas e monitoramento anual.", "ok"))
        else:
            recs.append(Recomendacao("Monitoramento estratégico",
                f"**{nome_alvo}** responde por {br(part)}% das emissões e varia {br(c, 1, True)}% ao ano. "
                "A ação deve ser proporcional, acompanhando riscos antes que o volume cresça.", "info"))

    share_carvao = dados.soma("coal_co2", alvo).get(fim, np.nan) / emissao_fim if emissao_fim > 0 else np.nan
    if pd.notna(share_carvao) and share_carvao >= LIMIAR_CARVAO:
        recs.append(Recomendacao("Matriz energética",
            f"O carvão representa **{br(share_carvao * 100, 0)}%** das emissões deste escopo. "
            "A substituição gradual por fontes de menor carbono gera redução rápida e mensurável.", "atencao"))

    co2_luc = dados.soma("co2_including_luc", alvo).get(fim, np.nan)
    share_luc = dados.soma("land_use_change_co2", alvo).get(fim, np.nan) / co2_luc if co2_luc > 0 else np.nan
    if pd.notna(share_luc) and share_luc >= LIMIAR_USO_TERRA:
        recs.append(Recomendacao("Uso da terra",
            f"Cerca de **{br(share_luc * 100, 0)}%** das emissões totais vêm da mudança no uso da terra. "
            "Conservação florestal e controle do desmatamento são ações imediatas (dado de maior incerteza).", "atencao"))

    populacao = dados.soma("population", alvo).get(fim, np.nan)
    pc_alvo = emissao_fim * 1e6 / populacao if populacao > 0 else np.nan
    pc_mundo = dados.mundo["co2_per_capita"].get(fim, np.nan)
    if pd.notna(pc_alvo) and pd.notna(pc_mundo):
        if pc_alvo > MULT_PER_CAPITA_ALTO * pc_mundo:
            recs.append(Recomendacao("Responsabilidade per capita",
                f"Com {br(pc_alvo)} t/hab, o escopo supera 2x a média mundial ({br(pc_mundo)} t/hab). "
                "Eficiência energética e metas absolutas são especialmente relevantes.", "atencao"))
        elif pc_alvo < MULT_PER_CAPITA_BAIXO * pc_mundo:
            recs.append(Recomendacao("Espaço de desenvolvimento",
                f"As {br(pc_alvo)} t/hab estão abaixo de metade da média mundial ({br(pc_mundo)} t/hab). "
                "O desafio é crescer mantendo tecnologia limpa desde o início.", "info"))

    ano = ano_pib(dados.matrizes, fim)
    pib = dados.soma("gdp", alvo).get(ano, 0)
    intensidade = dados.soma("co2", alvo).get(ano, np.nan) * 1e9 / pib if pib > 0 else np.nan
    pib_mundo = dados.matrizes["gdp"].loc[ano, dados.isos].sum(min_count=1)
    intensidade_mundo = dados.matrizes["co2"].loc[ano, dados.isos].sum(min_count=1) * 1e9 / pib_mundo if pib_mundo > 0 else np.nan
    if pd.notna(intensidade) and pd.notna(intensidade_mundo) and intensidade > MULT_INTENSIDADE_ALTA * intensidade_mundo:
        recs.append(Recomendacao("Eficiência econômica",
            f"A intensidade de {br(intensidade, 2)} kg/US$ passa de 1,5x a média mundial ({br(intensidade_mundo, 2)}). "
            "Modernização industrial e eficiência reduzem emissões e a exposição comercial.", "atencao"))

    if pd.notna(emissao_fim) and emissao_fim > 0:
        evitado = economia_acumulada(emissao_fim)
        recs.append(Recomendacao("Meta sugerida para mobilização",
            f"Reduzir **1% ao ano** evita cerca de **{br(evitado, 0)} Mt** acumulados em {ANOS_META} anos "
            "frente à emissão atual constante, sem exigir que o crescimento econômico seja interrompido.", "ok"))
    return recs
