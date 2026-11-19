"""Dashboard interativo de emissões de CO₂ para Jupyter e Google Colab.

Estrutura:
    dados_co2.py        leitura e organização dos dados
    indicadores_co2.py  cálculos, projeções e regras de decisão (sem interface)
    tema_co2.py         paleta, estilo dos gráficos e CSS
    dashboard_colab.py  este arquivo: widgets, gráficos e montagem do painel
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

import ipywidgets as widgets
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from IPython.display import HTML, display

from dados_co2 import BLOCOS, CONTINENTES, FONTES, PRIMEIRO_ANO, ULTIMO_ANO, Dados, ler_dados
from indicadores_co2 import (
    GRUPOS, MIN_EMISSAO_MT, ano_pib, benchmark, br, cagr, classificar_grupos, prever,
    recomendar, semaforo, simular_cenario, tabela_aceleracao,
)
from tema_co2 import (
    COR, COR_AREA, COR_APOIO, COR_BANDA, COR_DESTAQUE, COR_GRUPO, COR_SITUACAO, ESTILO_STATUS,
    PALETA, SEQUENCIA, formatar_figura, tematizar,
)

MARCOS = {1760: "Revolução Industrial", 1945: "Pós-Guerra", 2015: "Acordo de Paris"}
OPCOES_METRICA = ("Emissão total", "Per capita")
COR_POR_GRUPO = dict(zip(GRUPOS, COR_GRUPO))


# ----------------------------------------------------------------- blocos de texto e tabelas
def _inline(texto: str) -> str:
    """Escapa HTML e converte **negrito**."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(texto))


def _bloco(classe: str, texto: str) -> None:
    display(HTML(f'<div class="{classe}">{_inline(texto)}</div>'))


def titulo(texto: str) -> None:
    _bloco("co2-titulo", texto)


def subtitulo(texto: str) -> None:
    _bloco("co2-subtitulo", texto)


def nota(texto: str) -> None:
    _bloco("co2-nota", texto)


def vazio(texto: str) -> None:
    _bloco("co2-vazio", texto)


def emitir(fig, altura: int = 420) -> None:
    display(formatar_figura(fig, altura))


def tabela(df: pd.DataFrame, coluna_status: str | None = None) -> None:
    """Mostra um DataFrame no padrão pt-BR; `coluna_status` ganha as cores do semáforo."""
    if df.empty:
        vazio("Sem dados para os filtros atuais.")
        return
    try:
        estilo = df.style.format(precision=2, thousands=".", decimal=",")
        estilo = estilo.hide(axis="index") if hasattr(estilo, "hide") else estilo.hide_index()
        estilo = estilo.set_table_attributes('class="dataframe"')
        if coluna_status:
            aplicar = getattr(estilo, "map", None) or estilo.applymap
            estilo = aplicar(lambda v: ESTILO_STATUS.get(v, ""), subset=[coluna_status])
        display(estilo)
    except (ImportError, AttributeError, ValueError):
        display(df.round(2))


def cartoes_recomendacao(recomendacoes) -> None:
    itens = "".join(
        f'<div class="co2-rec co2-rec--{r.nivel}"><div class="co2-rec-titulo">{html.escape(r.titulo)}</div>'
        f"<div>{_inline(r.texto)}</div></div>"
        for r in recomendacoes
    )
    display(HTML(f'<div class="co2-recs">{itens}</div>'))


# ----------------------------------------------------------------- contexto dos filtros
@dataclass(frozen=True)
class Contexto:
    """Resultado dos filtros globais, calculado uma vez por atualização."""

    ini: int
    fim: int
    janela: int
    continente: str
    bloco: str
    permitidos: list
    escopo: list          # país em foco ou, se não houver, todos os permitidos
    iso_foco: str | None


def obter_contexto(dados: Dados, intervalo, continente, bloco, pais_foco, janela) -> Contexto:
    ini, fim = intervalo
    fim = max(fim, PRIMEIRO_ANO + janela)
    ini = min(ini, fim - 1)
    # Região e bloco definem a lista de comparação; o país em foco restringe só o escopo dos indicadores.
    permitidos = [
        iso for iso in dados.isos
        if (continente == "Todos" or dados.continentes.get(iso, "Outros") == continente)
        and (bloco == "Todos" or iso in BLOCOS[bloco])
    ]
    iso_foco = dados.nome_para_iso.get(pais_foco)
    escopo = [iso_foco] if iso_foco in dados.isos else permitidos
    return Contexto(ini, fim, janela, continente, bloco, permitidos, escopo, iso_foco)


def rotulo_escopo(dados: Dados, ctx: Contexto) -> str:
    if ctx.iso_foco in dados.isos:
        return dados.nomes[ctx.iso_foco]
    return ctx.bloco if ctx.bloco != "Todos" else ctx.continente if ctx.continente != "Todos" else "Mundo"


def coluna_metrica(metrica: str) -> tuple[str, str, bool]:
    """(coluna do dataset, unidade, é per capita?)."""
    per_capita = metrica == "Per capita"
    return ("co2_per_capita", "t/hab", True) if per_capita else ("co2", "Mt", False)


# ----------------------------------------------------------------- cartões de KPI
def exibir_kpis(dados: Dados, ctx: Contexto) -> None:
    total = dados.soma("co2", ctx.escopo)
    atual, anterior = total.get(ctx.fim, np.nan), total.get(ctx.fim - 1, np.nan)
    acumulado = total.loc[ctx.ini:ctx.fim].sum(min_count=1) / 1000
    variacao = atual / anterior - 1
    populacao = dados.soma("population", ctx.escopo).get(ctx.fim, np.nan)
    per_capita = atual * 1e6 / populacao if populacao and populacao > 0 else np.nan
    ranking = dados.matrizes["co2"].loc[ctx.fim].dropna().sort_values(ascending=False)

    if ctx.iso_foco in dados.isos:
        pos = ranking.index.get_loc(ctx.iso_foco) + 1 if ctx.iso_foco in ranking.index else None
        lider = (f"#{pos} de {len(ranking)}" if pos else "Sem dado", f"posição de {dados.nomes[ctx.iso_foco]}")
    else:
        ranqueados = [iso for iso in ranking.index if iso in ctx.permitidos]
        lider = ((dados.nomes[ranqueados[0]], f"{br(ranking[ranqueados[0]] / 1000)} Gt em {ctx.fim}")
                 if ranqueados else ("Sem dado", ""))

    tendencia = "co2-up" if pd.notna(variacao) and variacao > 0 else "co2-down"
    cartoes = [
        (f"Acumulado ({ctx.ini}–{ctx.fim})", f"{br(acumulado)} Gt", "soma do período filtrado", ""),
        (f"Variação {ctx.fim}/{ctx.fim - 1}", f"{br(variacao * 100, 1, True)}%",
         f"{br((atual - anterior) / 1000, 2, True)} Gt no ano", tendencia),
        ("Per capita", f"{br(per_capita, 2)} t/hab", f"emissão por habitante em {ctx.fim}", ""),
        ("Líder / posição", lider[0], lider[1], ""),
    ]
    itens = "".join(
        f'<div class="co2-kpi"><div class="co2-kpi-rotulo">{html.escape(r)}</div>'
        f'<div class="co2-kpi-valor {c}">{html.escape(v)}</div><div class="co2-kpi-ctx">{html.escape(x)}</div></div>'
        for r, v, x, c in cartoes
    )
    display(HTML(f'<div class="co2-kpis">{itens}</div>'))


# ----------------------------------------------------------------- aba 1: visão geral
def exibir_serie(dados: Dados, ctx: Contexto, metrica: str) -> None:
    _, unidade, per_capita = coluna_metrica(metrica)
    ts = pd.DataFrame({"co2": dados.soma("co2", ctx.escopo), "pop": dados.soma("population", ctx.escopo)})
    ts = ts.loc[ctx.ini:ctx.fim].dropna(subset=["co2"])
    ts["valor"] = ts.co2 * 1e6 / ts["pop"].where(ts["pop"] > 0) if per_capita else ts.co2 / 1000
    rotulo = rotulo_escopo(dados, ctx)
    if len(ts) > 1 and ts.co2.iloc[0] > 0:
        titulo(f"{rotulo}: emissões multiplicadas por {br(ts.co2.iloc[-1] / ts.co2.iloc[0])}x "
               f"entre {ts.index[0]} e {ts.index[-1]}")
    else:
        titulo(f"Emissões de {rotulo}: {ctx.ini}–{ctx.fim}")
    fig = px.area(ts.reset_index(), x="year", y="valor",
                  labels={"year": "Ano", "valor": unidade if per_capita else "Gt de CO₂"})
    fig.update_traces(line_color=COR, fillcolor=COR_AREA)
    for ano, marco in MARCOS.items():
        if len(ts) and ts.index.min() <= ano <= ts.index.max():
            fig.add_vline(x=ano, line_dash="dot", line_color=PALETA["borda_forte"], annotation_text=marco)
    emitir(fig, 380)


def exibir_mapa(dados: Dados, ctx: Contexto, metrica: str) -> None:
    coluna, unidade, _ = coluna_metrica(metrica)
    mapa = pd.DataFrame({
        "iso": ctx.permitidos, "País": [dados.nomes[i] for i in ctx.permitidos],
        "Valor": dados.matrizes[coluna].loc[ctx.fim, ctx.permitidos].values,
    }).dropna()
    if mapa.empty:
        return vazio("Sem dados para o mapa.")
    maior = mapa.sort_values("Valor", ascending=False).iloc[0]
    subtitulo(f"Mapa: {maior['País']} lidera em {ctx.fim} ({br(maior['Valor'])} {unidade})")
    fig = px.choropleth(mapa, locations="iso", color="Valor", hover_name="País", labels={"Valor": unidade})
    fig.update_geos(projection_type="natural earth")
    emitir(fig, 400)


def exibir_ranking(dados: Dados, ctx: Contexto, metrica: str) -> None:
    coluna, unidade, _ = coluna_metrica(metrica)
    historico = dados.matrizes["cumulative_co2"].loc[ctx.fim, ctx.permitidos].dropna().nlargest(10) / 1000
    atual = dados.matrizes[coluna].loc[ctx.fim, ctx.permitidos].dropna().nlargest(10)
    subtitulo("Top 10: histórico × atual")
    tabela(pd.DataFrame({
        "País (histórico)": [dados.nomes[i] for i in historico.index], "Acumulado (Gt)": historico.values,
        "País (atual)": [dados.nomes[i] for i in atual.index], f"Atual ({unidade})": atual.values,
    }))


def exibir_dispersao(dados: Dados, ctx: Contexto, metrica: str, eixo: str) -> None:
    coluna, unidade, _ = coluna_metrica(metrica)
    m, ap = dados.matrizes, ano_pib(dados.matrizes, ctx.fim)
    base = pd.DataFrame({
        "País": [dados.nomes[i] for i in ctx.permitidos],
        "PIB": m["gdp"].loc[ap, ctx.permitidos].values,
        "População": m["population"].loc[ctx.fim, ctx.permitidos].values,
        "Emissão": m[coluna].loc[ctx.fim, ctx.permitidos].values,
        "Intensidade": (m["co2"].loc[ap, ctx.permitidos] * 1e9 / m["gdp"].loc[ap, ctx.permitidos]).values,
    }).dropna()
    base = base[(base["PIB"] > 0) & (base["População"] > 0) & (base["Emissão"] > 0)]
    if base.empty:
        return vazio("Sem dados suficientes para a matriz de desigualdade.")
    pior = base.sort_values("Intensidade", ascending=False).iloc[0]
    titulo(f"Matriz de desigualdade (PIB de {ap}): {pior['País']} tem a maior intensidade, "
           f"{br(pior['Intensidade'], 2)} kg CO₂/US$")
    fig = px.scatter(base, x=eixo, y="Emissão", size="População" if eixo == "PIB" else "PIB",
                     color="Intensidade", hover_name="País", log_x=True, log_y=True, size_max=42,
                     labels={"Emissão": unidade, "Intensidade": "kg CO₂/US$"})
    emitir(fig, 440)


# ----------------------------------------------------------------- aba 2: pontos de inflexão
def exibir_deteccao(dados: Dados, ctx: Contexto, part_max, co2_min) -> None:
    tab = tabela_aceleracao(dados, ctx.permitidos, ctx.fim, ctx.janela)
    det = tab[(tab["CO₂ início (Mt)"] >= 1) & (tab["Participação inicial (%)"] < part_max)
              & (tab["CO₂ fim (Mt)"] >= co2_min)].dropna(subset=["Multiplicador"]).nlargest(15, "Multiplicador")
    if det.empty:
        titulo("Detector de crescimento acelerado")
        return vazio("Nenhum país atende aos critérios atuais.")
    topo = det.iloc[0]
    titulo(f"{topo['País']} multiplicou suas emissões por {br(topo['Multiplicador'])}x em {ctx.janela} anos")
    fig = px.bar(det.iloc[::-1], x="Multiplicador", y="País", orientation="h", color="Participação atual (%)")
    emitir(fig, 440)


def exibir_boom(dados: Dados, ctx: Contexto) -> None:
    iso_boom = ctx.iso_foco if ctx.iso_foco in dados.isos else "CHN"
    serie = dados.matrizes["co2"][iso_boom].dropna() if iso_boom in dados.isos else pd.Series(dtype=float)
    saltos = (serie - serie.shift(ctx.janela)).dropna()
    if saltos.empty:
        return
    ano_boom = int(saltos.idxmax())
    titulo(f"Antes e depois do boom: {dados.nomes[iso_boom]} (maior salto em {ano_boom})")
    fig = px.line(x=serie.index, y=serie.values, labels={"x": "Ano", "y": "Mt de CO₂"})
    fig.update_traces(line_color=COR)
    fig.add_vrect(x0=ano_boom - ctx.janela, x1=ano_boom, fillcolor=COR, opacity=0.2, line_width=0,
                  annotation_text="boom industrial", annotation_position="top left")
    emitir(fig, 340)


def exibir_crescimento_atual(dados: Dados, ctx: Contexto, co2_min, cresc_min, part_atual_max) -> None:
    tab = tabela_aceleracao(dados, ctx.permitidos, ctx.fim, ctx.janela)
    repeticao = tab[(tab["Crescimento a.a. (%)"] >= cresc_min) & (tab["Participação atual (%)"] <= part_atual_max)
                    & (tab["CO₂ fim (Mt)"] >= co2_min)].sort_values("Crescimento a.a. (%)", ascending=False)
    titulo(f"{len(repeticao)} países crescem hoje a {br(cresc_min)}% ao ano ou mais")
    tabela(repeticao.head(20))


# ----------------------------------------------------------------- aba 3: matriz e intensidade
def exibir_matriz(dados: Dados, ctx: Contexto, escala: str) -> None:
    m, ap = dados.matrizes, ano_pib(dados.matrizes, ctx.fim)
    top = m["co2"].loc[ctx.fim, ctx.permitidos].dropna().nlargest(10).index
    componentes = pd.DataFrame({nome: m[col].loc[ctx.fim, top] for col, nome in FONTES.items()}).fillna(0)
    componentes.index = [dados.nomes[i] for i in componentes.index]
    if escala == "Percentual":
        positivos = componentes.clip(lower=0)
        componentes = positivos.div(positivos.sum(axis=1).replace(0, np.nan), axis=0) * 100
    carvao = (m["coal_co2"].loc[ctx.fim, top] / m["co2"].loc[ctx.fim, top]).dropna()
    if len(carvao):
        titulo(f"O carvão responde por {br(carvao.max() * 100, 0)}% do CO₂ de {dados.nomes[carvao.idxmax()]}, "
               "o maior peso entre os 10 maiores emissores")
    else:
        titulo(f"Composição por fonte, Top 10 em {ctx.fim}")
    emitir(px.bar(componentes.iloc[::-1], orientation="h", barmode="stack", color_discrete_sequence=SEQUENCIA,
                  labels={"value": "%" if escala == "Percentual" else "Mt", "index": "", "variable": "Fonte"}), 400)

    ini = ap - ctx.janela
    pib0, pib1 = m["gdp"].loc[ini, ctx.permitidos], m["gdp"].loc[ap, ctx.permitidos]
    co20, co21 = m["co2"].loc[ini, ctx.permitidos], m["co2"].loc[ap, ctx.permitidos]
    eficiencia = pd.DataFrame({
        "País": [dados.nomes[i] for i in ctx.permitidos],
        "PIB (%)": ((pib1 / pib0 - 1) * 100).values, "CO₂ (%)": ((co21 / co20 - 1) * 100).values, "PIB": pib1.values,
    }).replace([np.inf, -np.inf], np.nan).dropna()
    if not eficiencia.empty:
        eficiencia["Situação"] = np.select(
            [(eficiencia["PIB (%)"] > 0) & (eficiencia["CO₂ (%)"] < 0),
             (eficiencia["PIB (%)"] > 0) & (eficiencia["CO₂ (%)"] < eficiencia["PIB (%)"])],
            ["Desacoplamento absoluto", "Desacoplamento relativo"], "Acoplado")
        absolutos = (eficiencia["Situação"] == "Desacoplamento absoluto").sum()
        titulo(f"{absolutos} países cresceram o PIB e reduziram as emissões entre {ini} e {ap}")
        emitir(px.scatter(eficiencia, x="PIB (%)", y="CO₂ (%)", size="PIB", color="Situação", hover_name="País",
                          size_max=40, color_discrete_map=COR_SITUACAO), 440)

    maiores = m["co2"].loc[ctx.fim, ctx.permitidos].dropna().nlargest(8).index
    intensidade = (m["co2"][maiores] * 1e9 / m["gdp"][maiores]).loc[1990:ap]
    intensidade.columns = [dados.nomes[i] for i in intensidade.columns]
    titulo(f"Intensidade de carbono dos 8 maiores emissores (kg CO₂/US$; PIB até {ap})")
    emitir(px.line(intensidade.reset_index().melt("year"), x="year", y="value", color="variable",
                   color_discrete_sequence=SEQUENCIA, labels={"year": "", "value": "kg CO₂/US$"}), 380)


# ----------------------------------------------------------------- aba 4: projeções
def serie_para_projecao(dados: Dados, nome: str) -> pd.Series:
    if nome == "Mundo":
        return dados.mundo["co2"]
    if nome in CONTINENTES:
        return dados.soma("co2", [i for i in dados.isos if dados.continentes.get(i) == nome])
    iso = dados.nome_para_iso.get(nome)
    return dados.matrizes["co2"][iso] if iso in dados.isos else pd.Series(dtype=float)


def exibir_projecoes(dados: Dados, ctx: Contexto, serie: str, reducao: float, troca: float) -> None:
    dados_serie = serie_para_projecao(dados, serie)
    previsao = prever(dados_serie)
    if previsao is None:
        titulo(f"Projeção até 2035: {serie}")
        vazio("Série sem dados suficientes para uma projeção.")
    else:
        anos_f = np.arange(ULTIMO_ANO + 1, ULTIMO_ANO + 1 + len(previsao.projecao))
        historico = dados_serie.dropna().loc[1990:ULTIMO_ANO] / 1000
        var_2035 = (previsao.projecao[-1] / dados_serie[ULTIMO_ANO] - 1) * 100
        titulo(f"{serie} deve emitir {br(previsao.projecao[-1] / 1000)} Gt em 2035 "
               f"({br(var_2035, 0, True)}% frente a {ULTIMO_ANO})")
        nota(f"Modelo escolhido no backtest: **{previsao.modelo}**, erro médio (MAPE) de **{br(previsao.mape)}%**. "
             f"Projeção para 2030: **{br(previsao.projecao[5] / 1000, 2)} Gt**."
             + (" **Atenção:** erro acima de 20%, use apenas como referência." if previsao.mape > 20 else ""))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=anos_f, y=(previsao.projecao + previsao.banda) / 1000, line={"width": 0},
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=anos_f, y=np.maximum(previsao.projecao - previsao.banda, 0) / 1000,
                                 fill="tonexty", fillcolor=COR_BANDA, line={"width": 0},
                                 name="Faixa de incerteza (~80%)", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=historico.index, y=historico.values, name="Histórico",
                                 line={"color": COR, "width": 2.5}))
        fig.add_trace(go.Scatter(x=anos_f, y=previsao.projecao / 1000, name="Projeção",
                                 line={"color": COR_DESTAQUE, "width": 2.5, "dash": "dash"}))
        fig.update_layout(yaxis_title="Gt de CO₂")
        emitir(fig, 380)

    cen = simular_cenario(dados, reducao, troca, ctx.janela)
    evitado = cen.base.iloc[-1] - cen.cenario.iloc[-1]
    titulo(f"Simulador: o cenário evita {br(evitado)} Gt por ano em 2035")
    nota(f"Os 5 maiores emissores ({', '.join(dados.nomes[i] for i in cen.top5)}) reduzem **{br(reducao)}% ao ano** e "
         f"**{cen.n_emergentes} países** em industrialização rápida trocam **{br(troca, 0)}%** do carvão. "
         "A referência de 2030 é aproximada (IPCC SR1.5) e deve ser conferida antes de ser citada.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cen.historico.index, y=cen.historico.values, name="Histórico",
                             line={"color": COR, "width": 2.5}))
    fig.add_trace(go.Scatter(x=cen.anos, y=cen.base.values, name="Linha de base",
                             line={"color": COR_APOIO, "width": 2.5, "dash": "dash"}))
    fig.add_trace(go.Scatter(x=cen.anos, y=cen.cenario.values, name="Cenário simulado",
                             line={"color": COR_DESTAQUE, "width": 2.5}))
    fig.add_trace(go.Scatter(x=[2030], y=[cen.referencia_2030], mode="markers", name="Referência aproximada 2030",
                             marker={"size": 11, "color": PALETA["alerta"]}))
    fig.update_layout(yaxis_title="Gt de CO₂", yaxis_rangemode="tozero")
    emitir(fig, 380)

    sem = semaforo(dados, ctx.permitidos, ctx.fim, ctx.janela)
    titulo("Semáforo de metas")
    nota("Verde: queda de pelo menos 1% ao ano. Amarelo: entre −1% e +2%. Vermelho: crescimento de 2% ao ano ou mais.")
    tabela(sem, coluna_status="Status")


# ----------------------------------------------------------------- aba 5: tomada de decisão
def exibir_decisao(dados: Dados, ctx: Contexto, volume: float, crescimento_alto: float) -> None:
    grupos = classificar_grupos(dados, ctx.permitidos, ctx.fim, ctx.janela, volume, crescimento_alto)
    grupo1 = grupos[grupos["Grupo"] == GRUPOS[0]]
    titulo(f"{len(grupo1)} países no Grupo 1 somam {br(grupo1['Participação (%)'].sum())}% das emissões globais")
    fig = px.scatter(grupos, x="CO₂ (Mt)", y="Crescimento a.a. (%)", color="Grupo", size="Participação (%)",
                     hover_name="País", log_x=True, size_max=42, color_discrete_map=COR_POR_GRUPO,
                     category_orders={"Grupo": list(GRUPOS)})
    fig.add_hline(y=crescimento_alto, line_dash="dot", line_color=PALETA["borda_forte"])
    fig.add_vline(x=volume / 100 * dados.mundo["co2"].get(ctx.fim, np.nan), line_dash="dot",
                  line_color=PALETA["borda_forte"])
    emitir(fig, 440)
    resumo = grupos.groupby("Grupo").apply(lambda g: pd.Series({
        "Países": len(g), "% das emissões": g["Participação (%)"].sum(),
        "Principais": ", ".join(g.nlargest(5, "CO₂ (Mt)")["País"])}), include_groups=False)
    tabela(resumo.reindex(list(GRUPOS)).dropna(how="all").reset_index())

    alvo = ctx.escopo
    nome_alvo = dados.nomes[ctx.iso_foco] if ctx.iso_foco in dados.isos else "seleção atual"
    titulo(f"Plano de ação para {nome_alvo}")
    cartoes_recomendacao(recomendar(dados, alvo, nome_alvo, ctx.fim, ctx.janela, volume, crescimento_alto))

    ap = ano_pib(dados.matrizes, ctx.fim)
    referencias = benchmark(dados, alvo, ap, ctx.janela)
    titulo(f"Benchmark de desacoplamento (PIB até {ap})")
    if referencias.empty:
        vazio("Nenhuma referência comparável com desacoplamento foi encontrada.")
    else:
        nota(f"Economias de renda parecida com **{nome_alvo}** que cresceram o PIB e reduziram o CO₂: "
             f"**{', '.join(referencias['País'])}**.")
        tabela(referencias)


# ----------------------------------------------------------------- montagem do painel
def _campo(rotulo: str, controle: widgets.Widget) -> widgets.VBox:
    """Rótulo acima do controle (cabe melhor no painel lateral estreito)."""
    return widgets.VBox([widgets.HTML(f'<div class="co2-rotulo">{html.escape(rotulo)}</div>'), controle])


def _slider(rotulo: str, valor, minimo, maximo, passo) -> widgets.VBox:
    cls = widgets.FloatSlider if isinstance(passo, float) else widgets.IntSlider
    extra = {"readout_format": ".1f"} if cls is widgets.FloatSlider else {}
    slider = cls(value=valor, min=minimo, max=maximo, step=passo, continuous_update=False,
                 layout=widgets.Layout(width="100%"), **extra)
    campo = _campo(rotulo, slider)
    campo.slider = slider
    return campo


def _aba(controles: list, conteudo: widgets.Widget, largura_total: tuple = ()) -> widgets.GridBox:
    """Controles à esquerda (280 px) e resultados à direita; `largura_total` ocupa a linha inteira."""
    lateral = widgets.VBox(controles)
    lateral.add_class("co2-controles")
    for bloco in largura_total:
        bloco.layout.grid_column = "1 / -1"
    grade = widgets.GridBox([lateral, conteudo, *largura_total], layout=widgets.Layout(
        width="100%", grid_template_columns="280px minmax(0, 1fr)", grid_gap="0 18px"))
    grade.add_class("co2-aba")
    return grade


@tematizar
def criar_dashboard(caminho_csv: str | None = None) -> widgets.VBox:
    """Carrega os dados e devolve o painel (use `display(criar_dashboard())`)."""
    dados = ler_dados(caminho_csv)
    paises = sorted(dados.nomes.dropna().tolist())
    rotulo_largo = {"description_width": "110px"}
    cheio = widgets.Layout(width="100%")

    # filtros globais
    anos = widgets.IntRangeSlider(value=(1850, ULTIMO_ANO), min=PRIMEIRO_ANO, max=ULTIMO_ANO, description="Anos",
                                  continuous_update=False, style=rotulo_largo, layout=cheio)
    janela = widgets.IntSlider(value=10, min=5, max=20, description="Janela (anos)", continuous_update=False,
                               style=rotulo_largo, layout=cheio)
    continente = widgets.Dropdown(options=["Todos", *CONTINENTES], value="Todos", description="Continente",
                                  style=rotulo_largo, layout=cheio)
    bloco = widgets.Dropdown(options=["Todos", *BLOCOS], value="Todos", description="Bloco",
                             style=rotulo_largo, layout=cheio)
    foco = widgets.Dropdown(options=["Nenhum", *paises], value="Nenhum", description="País em foco",
                            style=rotulo_largo, layout=cheio)

    # controles de cada aba
    metrica = widgets.ToggleButtons(options=OPCOES_METRICA, value=OPCOES_METRICA[0])
    eixo = widgets.ToggleButtons(options=["PIB", "População"], value="PIB")
    part_max, co2_min = _slider("Participação inicial máxima (%)", 2.0, 0.1, 5.0, 0.1), _slider("CO₂ mínimo no fim (Mt)", 20, 5, 200, 5)
    cresc_min, part_atual = _slider("Crescimento mínimo (% a.a.)", 3.0, 1.0, 10.0, 0.5), _slider("Participação atual máxima (%)", 5.0, 1.0, 15.0, 0.5)
    escala = widgets.ToggleButtons(options=["Absoluta (Mt)", "Percentual"], value="Absoluta (Mt)")
    serie = widgets.Dropdown(options=["Mundo", *CONTINENTES, *paises], value="Mundo", layout=cheio)
    reducao, troca = _slider("Redução anual dos 5 maiores (%)", 3.0, 0.0, 10.0, 0.5), _slider("Troca de carvão nos emergentes (%)", 30, 0, 100, 5)
    volume, cresc_alto = _slider("Volume alto: participação mínima (%)", 2.0, 0.5, 10.0, 0.5), _slider("Crescimento alto (% a.a.)", 1.0, -2.0, 5.0, 0.5)

    comuns = {"intervalo": anos, "continente": continente, "bloco": bloco, "pais_foco": foco, "janela": janela}

    def saida(funcao, exige_escopo: bool = True, **extras) -> widgets.Output:
        """Liga uma função de exibição aos filtros globais e aos controles extras."""
        def atualizar(**valores):
            ctx = obter_contexto(dados, *(valores.pop(k) for k in comuns))
            if exige_escopo and not ctx.escopo:
                return vazio("Nenhum país atende aos filtros.")
            funcao(dados, ctx, **valores)
        # O ipywidgets chama essa função sempre que um filtro associado muda.
        return widgets.interactive_output(atualizar, {**comuns, **extras})

    out_kpis = saida(exibir_kpis)
    aba_geral = _aba(
        [_campo("Métrica", metrica), _campo("Eixo X da dispersão", eixo)],
        widgets.VBox([
            saida(exibir_serie, metrica=metrica),
            widgets.GridBox([saida(exibir_mapa, metrica=metrica), saida(exibir_ranking, metrica=metrica)],
                            layout=widgets.Layout(width="100%", grid_template_columns="3fr 2fr", grid_gap="18px")),
            saida(exibir_dispersao, metrica=metrica, eixo=eixo),
        ]),
    )
    aba_geral.children[1].children[1].add_class("co2-par")
    aba_inflexao = _aba(
        [part_max, co2_min, cresc_min, part_atual],
        saida(exibir_deteccao, exige_escopo=False, part_max=part_max.slider, co2_min=co2_min.slider),
        largura_total=(
            saida(exibir_boom, exige_escopo=False),
            saida(exibir_crescimento_atual, exige_escopo=False, co2_min=co2_min.slider,
                  cresc_min=cresc_min.slider, part_atual_max=part_atual.slider),
        ))
    aba_matriz = _aba([_campo("Escala", escala)], saida(exibir_matriz, escala=escala))
    aba_projecao = _aba(
        [_campo("Série", serie), reducao, troca],
        saida(exibir_projecoes, exige_escopo=False, serie=serie, reducao=reducao.slider, troca=troca.slider))
    aba_decisao = _aba(
        [volume, cresc_alto],
        saida(exibir_decisao, volume=volume.slider, crescimento_alto=cresc_alto.slider))

    abas = widgets.Tab(children=[aba_geral, aba_inflexao, aba_matriz, aba_projecao, aba_decisao])
    for i, nome in enumerate(["Visão geral", "Pontos de inflexão", "Matriz e intensidade", "Projeções", "Decisão"]):
        abas.set_title(i, nome)
    abas.add_class("co2-abas")

    hero = widgets.HTML(
        "<h1>Emissões de CO₂ — Painel Executivo</h1>"
        '<p><span class="co2-eyebrow">Projeto de Análise de Dados e BI</span>'
        f"{PRIMEIRO_ANO}–{ULTIMO_ANO} · histórico · responsabilidade · transição energética</p>")
    hero.add_class("co2-hero")
    topo = widgets.VBox([hero, out_kpis])
    topo.add_class("co2-topo")

    barra = widgets.GridBox([continente, bloco, foco], layout=widgets.Layout(
        width="100%", grid_template_columns="repeat(3, minmax(0, 1fr))", grid_gap="12px 24px"))
    barra.add_class("co2-par")
    linha_anos = widgets.GridBox([anos, janela], layout=widgets.Layout(
        width="100%", grid_template_columns="repeat(2, minmax(0, 1fr))", grid_gap="12px 24px", margin="0 0 12px 0"))
    linha_anos.add_class("co2-par")
    filtros = widgets.VBox([
        widgets.HTML("<h3>Filtros globais</h3>"), linha_anos, barra,
        widgets.HTML("<small>Dados: Our World in Data / Global Carbon Project. Países com os nomes originais do "
                     "dataset. Escolha um país em foco para priorizá-lo nos indicadores.</small>")])
    filtros.add_class("co2-filtros")
    return widgets.VBox([topo, filtros, abas])


if __name__ == "__main__":
    display(criar_dashboard())
