"""Dashboard interativo de emissões de CO₂ para Jupyter e Google Colab."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ipywidgets as widgets
from IPython.display import Markdown, display
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from tema_co2 import COR, COR_SECUNDARIA, GRUPOS_COR, _formatar, tematizar


DATA_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
ULTIMO_ANO = 2024

CONTINENTES = {
    "África": "DZA AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COG COD CIV DJI EGY GNQ ERI SWZ ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS MAR MOZ NAM NER NGA RWA STP SEN SYC SLE SOM ZAF SSD SDN TZA TGO TUN UGA ZMB ZWE ESH SHN REU MYT",
    "Ásia": "AFG ARM AZE BHR BGD BTN BRN KHM CHN GEO IND IDN IRN IRQ ISR JPN JOR KAZ KWT KGZ LAO LBN MYS MDV MNG MMR NPL PRK OMN PAK PSE PHL QAT SAU SGP KOR LKA SYR TWN TJK THA TLS TUR TKM ARE UZB VNM YEM HKG MAC",
    "Europa": "ALB AND AUT BLR BEL BIH BGR HRV CYP CZE DNK EST FRO FIN FRA DEU GIB GRC HUN ISL IRL ITA OWID_KOS LVA LIE LTU LUX MLT MDA MCO MNE NLD MKD NOR POL PRT ROU RUS SMR SRB SVK SVN ESP SWE CHE UKR GBR VAT IMN GGY JEY",
    "América do Norte": "ATG BHS BRB BLZ CAN CRI CUB DMA DOM SLV GRD GTM HTI HND JAM MEX NIC PAN KNA LCA VCT TTO USA ABW AIA BMU CYM CUW GLP GRL MTQ MSR PRI SPM SXM TCA VGB VIR BES MAF",
    "América do Sul": "ARG BOL BRA CHL COL ECU GUY PRY PER SUR URY VEN FLK GUF",
    "Oceania": "AUS FJI KIR MHL FSM NRU NZL PLW PNG WSM SLB TON TUV VUT COK NIU NCL PYF ASM GUM MNP TKL WLF PCN",
}
ISO_PARA_CONTINENTE = {
    iso: continente
    for continente, codigos in CONTINENTES.items()
    for iso in codigos.split()
}
BLOCOS = {
    "G20": set("ARG AUS BRA CAN CHN FRA DEU IND IDN ITA JPN KOR MEX RUS SAU ZAF TUR GBR USA".split()),
    "BRICS": set("BRA RUS IND CHN ZAF EGY ETH IRN ARE".split()),
    "União Europeia": set("AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE".split()),
}
FONTES = {
    "coal_co2": "Carvão",
    "oil_co2": "Petróleo",
    "gas_co2": "Gás natural",
    "cement_co2": "Cimento",
    "flaring_co2": "Queima (flaring)",
    "land_use_change_co2": "Uso da terra",
}
COLUNAS = [
    "country", "year", "iso_code", "co2", "population", "gdp", "co2_per_capita",
    "coal_co2", "oil_co2", "gas_co2", "cement_co2", "flaring_co2",
    "land_use_change_co2", "co2_including_luc", "cumulative_co2",
]


def _ler_dados(caminho_csv=None):
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
        dados = pd.read_csv(arquivo, usecols=lambda c: c in COLUNAS)
    else:
        print("Arquivo local não encontrado; baixando o dataset da Our World in Data.")
        dados = pd.read_csv(DATA_URL, usecols=lambda c: c in COLUNAS)

    faltantes = set(COLUNAS) - set(dados.columns)
    if faltantes:
        raise ValueError(f"O dataset não contém as colunas necessárias: {', '.join(sorted(faltantes))}")
    dados = dados.loc[dados["year"] <= ULTIMO_ANO].copy()
    dados["year"] = dados["year"].astype(int)
    mundo = dados.loc[dados["country"] == "World"].set_index("year")
    iso = dados["iso_code"].astype("string")
    paises = dados.loc[
        dados["iso_code"].notna()
        & (~iso.str.startswith("OWID_", na=False) | iso.eq("OWID_KOS"))
    ].copy()
    anos = range(1750, ULTIMO_ANO + 1)
    colunas_matriz = [c for c in COLUNAS if c not in {"country", "iso_code", "year"}]
    matrizes = {
        coluna: paises.pivot(index="year", columns="iso_code", values=coluna).reindex(anos)
        for coluna in colunas_matriz
    }
    info = paises.drop_duplicates("iso_code").set_index("iso_code")
    nomes = info["country"]
    continentes = pd.Series(
        {codigo: ISO_PARA_CONTINENTE.get(codigo, "Outros") for codigo in info.index}
    )
    if mundo.empty or ULTIMO_ANO not in mundo.index:
        raise ValueError(f"O dataset não contém dados agregados do mundo para {ULTIMO_ANO}.")
    return matrizes, mundo, nomes, continentes


def _cagr(inicio, fim, anos):
    if anos <= 0:
        return inicio * np.nan
    resultado = (fim / inicio) ** (1 / anos) - 1
    return resultado.where((inicio > 0) & (fim > 0))


def _ano_pib(matrizes, fim):
    contagem = matrizes["gdp"].loc[:fim].notna().sum(axis=1)
    suficiente = contagem[contagem >= 0.5 * contagem.max()]
    if suficiente.empty:
        return fim
    return int(suficiente.index.max())


def _prever(serie, horizonte=11):
    historico = serie.dropna().loc[1950:ULTIMO_ANO]
    if len(historico) < 40 or historico.index[-1] != ULTIMO_ANO:
        return None

    valores = historico.to_numpy(dtype=float)

    def linear(amostra, passos):
        x = np.arange(len(amostra))[-15:]
        return np.polyval(
            np.polyfit(x, amostra[-15:], 1),
            np.arange(len(amostra), len(amostra) + passos),
        )

    def drift(amostra, passos):
        return amostra[-1] + (amostra[-1] - amostra[-16]) / 15 * np.arange(1, passos + 1)

    modelos = {
        "Tendência linear (15 anos)": linear,
        "Drift (15 anos)": drift,
        "Holt amortecido": lambda y, h: ExponentialSmoothing(
            y, trend="add", damped_trend=True
        ).fit().forecast(h),
    }
    resultados = {}
    for nome, modelo in modelos.items():
        try:
            erro = np.asarray(modelo(valores[:-10], 10)) - valores[-10:]
            resultados[nome] = (
                float(np.mean(np.abs(erro) / np.abs(valores[-10:])) * 100),
                float(np.sqrt(np.mean(erro**2))),
                np.asarray(modelo(valores, horizonte)),
            )
        except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as erro:
            print(f"Modelo {nome} ignorado no backtest: {erro}")
    if not resultados:
        return None
    melhor = min(resultados, key=lambda nome: resultados[nome][0])
    mape, rmse, projecao = resultados[melhor]
    banda = 1.28 * rmse * np.sqrt(np.arange(1, horizonte + 1) / 5)
    return melhor, mape, projecao, banda


def criar_dashboard(caminho_csv=None):
    """Carrega dados e exibe o dashboard com controles nativos de notebook."""
    matrizes, mundo, nomes, continentes = _ler_dados(caminho_csv)
    isos = list(matrizes["co2"].columns)
    nome_para_iso = {nome: iso for iso, nome in nomes.items()}
    paises = sorted(nomes.dropna().tolist())

    anos = widgets.IntRangeSlider(
        value=(1850, ULTIMO_ANO), min=1750, max=ULTIMO_ANO, step=1,
        description="Anos", continuous_update=False, layout=widgets.Layout(width="430px"),
    )
    filtro_continente = widgets.SelectMultiple(
        options=list(CONTINENTES), description="Continentes",
        layout=widgets.Layout(width="250px", height="110px"),
    )
    filtro_bloco = widgets.Dropdown(
        options=["Todos", *BLOCOS], description="Bloco",
        layout=widgets.Layout(width="230px"),
    )
    foco = widgets.Dropdown(
        options=["Nenhum", *paises], value="Nenhum", description="País em foco",
        layout=widgets.Layout(width="370px"),
    )
    metrica = widgets.ToggleButtons(
        options=["Emissão total (Mt)", "Per capita (t/hab)"],
        description="Métrica", button_style="",
    )
    janela = widgets.IntSlider(
        value=10, min=5, max=20, description="Janela (anos)",
        continuous_update=False, layout=widgets.Layout(width="350px"),
    )
    detector_part = widgets.FloatSlider(
        value=2, min=0.1, max=5, step=0.1, description="Part. inicial máx. (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )
    emissao_min = widgets.IntSlider(
        value=20, min=5, max=200, step=5, description="CO₂ mínimo (Mt)",
        continuous_update=False, layout=widgets.Layout(width="400px"),
    )
    crescimento_rep = widgets.FloatSlider(
        value=3, min=1, max=10, step=0.5, description="Cresc. mínimo (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )
    part_rep = widgets.FloatSlider(
        value=5, min=1, max=15, step=0.5, description="Part. atual máx. (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )
    escala_fontes = widgets.ToggleButtons(
        options=["Absoluta (Mt)", "Percentual"], description="Escala",
    )
    eixo_scatter = widgets.ToggleButtons(options=["PIB", "População"], description="Eixo X")
    serie_previsao = widgets.Dropdown(
        options=["Mundo", *CONTINENTES, *paises], value="Mundo",
        description="Série", layout=widgets.Layout(width="400px"),
    )
    reducao_top5 = widgets.FloatSlider(
        value=3, min=0, max=10, step=0.5, description="Redução anual (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )
    troca_carvao = widgets.IntSlider(
        value=30, min=0, max=100, step=5, description="Troca do carvão (%)",
        continuous_update=False, layout=widgets.Layout(width="400px"),
    )
    limiar_volume = widgets.FloatSlider(
        value=2, min=0.5, max=10, step=0.5, description="Volume alto (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )
    limiar_crescimento = widgets.FloatSlider(
        value=1, min=-2, max=5, step=0.5, description="Cresc. alto (%)",
        readout_format=".1f", continuous_update=False,
        layout=widgets.Layout(width="400px"),
    )

    def obter_contexto(intervalo, conts, bloco, pais_foco):
        ini, fim = intervalo
        fim = max(fim, 1750 + janela.value)
        permitidos = [
            iso for iso in isos
            if (not conts or continentes.get(iso, "Outros") in conts)
            and (bloco == "Todos" or iso in BLOCOS[bloco])
        ]
        iso_foco = nome_para_iso.get(pais_foco)
        escopo = [iso_foco] if iso_foco in isos else permitidos
        return ini, fim, permitidos, escopo, iso_foco

    def soma(serie, selecionados):
        if not selecionados:
            return pd.Series(np.nan, index=serie.index)
        return serie.loc[:, selecionados].sum(axis=1, min_count=1)

    def emitir(fig):
        display(_formatar(fig))

    def texto(conteudo):
        display(Markdown(conteudo))

    def kpis(intervalo, conts, bloco, pais_foco, janela_atual):
        ini, fim, permitidos, escopo, iso_foco = obter_contexto(
            intervalo, conts, bloco, pais_foco
        )
        if not escopo:
            texto("Nenhum país atende aos filtros.")
            return
        total = soma(matrizes["co2"], escopo)
        acumulado = total.loc[ini:fim].sum(min_count=1) / 1000
        variacao = total.get(fim, np.nan) / total.get(fim - 1, np.nan) - 1
        populacao = soma(matrizes["population"], escopo).get(fim, np.nan)
        emis_fim = soma(matrizes["co2"], escopo).get(fim, np.nan)
        pc = emis_fim * 1e6 / populacao if populacao and populacao > 0 else np.nan
        ranking = matrizes["co2"].loc[fim].dropna().sort_values(ascending=False)
        if iso_foco in isos:
            pos = ranking.index.get_loc(iso_foco) + 1 if iso_foco in ranking.index else None
            lider = f"{nomes[iso_foco]}: #{pos}" if pos else "Sem dado"
        else:
            ranked = [iso for iso in ranking.index if iso in permitidos]
            lider = nomes[ranked[0]] if ranked else "Sem dado"
        cards = widgets.HBox([
            widgets.HTML(f"<b>Acumulado ({ini}–{fim})</b><br>{acumulado:,.1f} Gt"),
            widgets.HTML(f"<b>Variação {fim}/{fim-1}</b><br>{variacao:+.1%}" if pd.notna(variacao) else "<b>Variação anual</b><br>Sem dado"),
            widgets.HTML(f"<b>Per capita</b><br>{pc:,.2f} t/hab" if pd.notna(pc) else "<b>Per capita</b><br>Sem dado"),
            widgets.HTML(f"<b>Líder / posição</b><br>{lider}"),
        ], layout=widgets.Layout(justify_content="space-between", width="100%"))
        display(cards)

    def visao(intervalo, conts, bloco, pais_foco, janela_atual, metrica_atual, eixo):
        ini, fim, permitidos, escopo, iso_foco = obter_contexto(
            intervalo, conts, bloco, pais_foco
        )
        if not escopo:
            texto("Nenhum país atende aos filtros.")
            return
        total = soma(matrizes["co2"], escopo)
        populacao = soma(matrizes["population"], escopo)
        ts = pd.DataFrame({"co2": total, "pop": populacao}).loc[ini:fim].dropna(subset=["co2"])
        per_capita = metrica_atual.startswith("Per capita")
        ts["valor"] = ts.co2 * 1e6 / ts["pop"].where(ts["pop"] > 0) if per_capita else ts.co2 / 1000
        rotulo = nomes[iso_foco] if iso_foco in isos else bloco if bloco != "Todos" else "Mundo/seleção"
        texto(f"### Emissões de {rotulo}: {ini}–{fim}")
        fig = px.area(
            ts.reset_index(), x="year", y="valor", color_discrete_sequence=[COR],
            labels={"year": "Ano", "valor": "t/hab" if per_capita else "Gt de CO₂"},
        )
        for ano, marco in {1760: "Revolução Industrial", 1945: "Pós-Guerra", 2015: "Acordo de Paris"}.items():
            if len(ts) and ts.index.min() <= ano <= ts.index.max():
                fig.add_vline(x=ano, line_dash="dot", annotation_text=marco)
        emitir(fig)

        mapa = pd.DataFrame({
            "iso": permitidos,
            "País": [nomes[i] for i in permitidos],
            "Valor": matrizes["co2_per_capita" if per_capita else "co2"].loc[fim, permitidos].values,
        }).dropna()
        if not mapa.empty:
            texto("#### Mapa e rankings")
            fig_mapa = px.choropleth(
                mapa, locations="iso", color="Valor", hover_name="País",
                color_continuous_scale="YlOrBr",
                labels={"Valor": "t/hab" if per_capita else "Mt"},
            )
            fig_mapa.update_geos(showframe=False, projection_type="natural earth")
            emitir(fig_mapa)
            historico = matrizes["cumulative_co2"].loc[fim, permitidos].dropna().nlargest(10) / 1000
            atual = matrizes["co2_per_capita" if per_capita else "co2"].loc[fim, permitidos].dropna().nlargest(10)
            texto("#### Top 10 histórico e atual")
            display(pd.DataFrame({
                "País (histórico)": [nomes[i] for i in historico.index],
                "Acumulado (Gt)": historico.values,
                "País (atual)": [nomes[i] for i in atual.index],
                f"Emissão atual ({'t/hab' if per_capita else 'Mt'})": atual.values,
            }).round(2))

        ap = _ano_pib(matrizes, fim)
        yval = matrizes["co2_per_capita" if per_capita else "co2"].loc[fim, permitidos]
        intensidade = matrizes["co2"].loc[ap, permitidos] * 1e9 / matrizes["gdp"].loc[ap, permitidos]
        pop = matrizes["population"].loc[fim, permitidos]
        dados = pd.DataFrame({
            "País": [nomes[i] for i in permitidos],
            "PIB": matrizes["gdp"].loc[ap, permitidos].values,
            "População": pop.values,
            "Emissão": yval.values,
            "Intensidade": intensidade.values,
        }).dropna()
        dados = dados[(dados["PIB"] > 0) & (dados["População"] > 0) & (dados["Emissão"] > 0)]
        if not dados.empty:
            texto(f"#### Matriz de desigualdade — PIB de {ap}")
            emitir(px.scatter(
                dados, x=eixo, y="Emissão", size="População" if eixo == "PIB" else "PIB",
                color="Intensidade", hover_name="País", log_x=True, log_y=True,
                size_max=42, color_continuous_scale="YlOrRd",
                labels={"Emissão": "t/hab" if per_capita else "Mt", "Intensidade": "kg CO₂/US$"},
            ))

    def inflexoes(intervalo, conts, bloco, pais_foco, janela_atual, part_max, co2_min, cresc_min, part_atual_max):
        _, fim, permitidos, _, iso_foco = obter_contexto(intervalo, conts, bloco, pais_foco)
        ini_j = fim - janela_atual
        inicio = matrizes["co2"].loc[ini_j, permitidos]
        final = matrizes["co2"].loc[fim, permitidos]
        participacao_inicio = inicio / mundo["co2"].get(ini_j, np.nan) * 100
        participacao_fim = final / mundo["co2"].get(fim, np.nan) * 100
        tabela = pd.DataFrame({
            "País": [nomes[i] for i in permitidos],
            "CO₂ início (Mt)": inicio.values, "CO₂ fim (Mt)": final.values,
            "Multiplicador": (final / inicio).values,
            "Participação inicial (%)": participacao_inicio.values,
            "Participação atual (%)": participacao_fim.values,
            "Crescimento a.a. (%)": (_cagr(inicio, final, janela_atual) * 100).values,
        })
        texto("### Detector de crescimento acelerado")
        det = tabela[
            (tabela["CO₂ início (Mt)"] >= 1)
            & (tabela["Participação inicial (%)"] < part_max)
            & (tabela["CO₂ fim (Mt)"] >= co2_min)
        ].dropna(subset=["Multiplicador"]).nlargest(15, "Multiplicador")
        if not det.empty:
            texto(f"Maior multiplicador: **{det.iloc[0]['País']} — {det.iloc[0]['Multiplicador']:.1f}x** em {janela_atual} anos.")
            emitir(px.bar(det.iloc[::-1], x="Multiplicador", y="País", orientation="h", color="Participação atual (%)", color_continuous_scale="YlOrRd"))
        else:
            texto("Nenhum país atende aos critérios atuais.")

        iso_boom = iso_foco if iso_foco in isos else "CHN"
        if iso_boom in isos:
            serie = matrizes["co2"][iso_boom].dropna()
            saltos = (serie - serie.shift(janela_atual)).dropna()
            if not saltos.empty:
                ano_boom = int(saltos.idxmax())
                texto(f"### Antes/depois do boom: {nomes[iso_boom]} (maior salto em {ano_boom})")
                emitir(px.line(x=serie.index, y=serie.values, labels={"x": "Ano", "y": "Mt de CO₂"}))
        repeticao = tabela[
            (tabela["Crescimento a.a. (%)"] >= cresc_min)
            & (tabela["Participação atual (%)"] <= part_atual_max)
            & (tabela["CO₂ fim (Mt)"] >= co2_min)
        ].sort_values("Crescimento a.a. (%)", ascending=False)
        texto("### Países em crescimento acelerado hoje")
        display(repeticao.head(20).round(2))

    def matriz_fontes(intervalo, conts, bloco, pais_foco, janela_atual, escala):
        _, fim, permitidos, _, _ = obter_contexto(intervalo, conts, bloco, pais_foco)
        top = matrizes["co2"].loc[fim, permitidos].dropna().nlargest(10).index
        componentes = pd.DataFrame({
            nome: matrizes[col].loc[fim, top] for col, nome in FONTES.items()
        }).fillna(0)
        componentes.index = [nomes[i] for i in componentes.index]
        if escala == "Percentual":
            componentes = componentes.clip(lower=0).div(
                componentes.clip(lower=0).sum(axis=1).replace(0, np.nan), axis=0
            ) * 100
        texto(f"### Composição por fonte — Top 10 em {fim}")
        emitir(px.bar(componentes.iloc[::-1], orientation="h", barmode="stack"))

        ap = _ano_pib(matrizes, fim)
        gdp0, gdp1 = matrizes["gdp"].loc[ap - janela_atual, permitidos], matrizes["gdp"].loc[ap, permitidos]
        co20, co21 = matrizes["co2"].loc[ap - janela_atual, permitidos], matrizes["co2"].loc[ap, permitidos]
        eficiencia = pd.DataFrame({
            "País": [nomes[i] for i in permitidos],
            "PIB (%)": ((gdp1 / gdp0 - 1) * 100).values,
            "CO₂ (%)": ((co21 / co20 - 1) * 100).values,
            "PIB": gdp1.values,
        }).replace([np.inf, -np.inf], np.nan).dropna()
        if not eficiencia.empty:
            eficiencia["Situação"] = np.select(
                [(eficiencia["PIB (%)"] > 0) & (eficiencia["CO₂ (%)"] < 0),
                 (eficiencia["PIB (%)"] > 0) & (eficiencia["CO₂ (%)"] < eficiencia["PIB (%)"])],
                ["Desacoplamento absoluto", "Desacoplamento relativo"], "Acoplado",
            )
            texto(f"### PIB × CO₂ ({ap-janela_atual}–{ap}) — {(eficiencia['Situação'] == 'Desacoplamento absoluto').sum()} casos de desacoplamento absoluto")
            emitir(px.scatter(eficiencia, x="PIB (%)", y="CO₂ (%)", size="PIB", color="Situação", hover_name="País", size_max=40))
        maiores = matrizes["co2"].loc[fim, permitidos].dropna().nlargest(8).index
        intensidade = (
            matrizes["co2"][maiores] * 1e9 / matrizes["gdp"][maiores]
        ).loc[1990:ap]
        intensidade.columns = [nomes[i] for i in intensidade.columns]
        texto(f"### Intensidade de carbono (kg CO₂/US$; PIB até {ap})")
        emitir(px.line(intensidade.reset_index().melt("year"), x="year", y="value", color="variable"))

    def previsao(intervalo, conts, bloco, pais_foco, janela_atual, serie, reducao, troca):
        texto("### Projeção até 2035")
        if serie == "Mundo":
            dados_serie = mundo["co2"]
        elif serie in CONTINENTES:
            iso_cont = [i for i in isos if continentes.get(i) == serie]
            dados_serie = soma(matrizes["co2"], iso_cont)
        else:
            iso = nome_para_iso.get(serie)
            dados_serie = matrizes["co2"][iso] if iso in isos else pd.Series(dtype=float)
        resultado = _prever(dados_serie)
        if resultado is None:
            texto("Série sem dados suficientes para uma projeção.")
        else:
            modelo, mape, fc, banda = resultado
            anos_f = np.arange(ULTIMO_ANO + 1, ULTIMO_ANO + 12)
            historico = dados_serie.dropna().loc[1990:ULTIMO_ANO] / 1000
            variacao = (fc[-1] / dados_serie[ULTIMO_ANO] - 1) * 100
            texto(f"{serie}: **{fc[-1]/1000:.1f} Gt em 2035 ({variacao:+.0f}% vs. {ULTIMO_ANO})**; modelo **{modelo}**, MAPE do backtest **{mape:.1f}%**.")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=anos_f, y=(fc + banda) / 1000, line={"width": 0}, showlegend=False))
            fig.add_trace(go.Scatter(x=anos_f, y=np.maximum(fc - banda, 0) / 1000, fill="tonexty", line={"width": 0}, name="Faixa de incerteza (~80%)"))
            fig.add_trace(go.Scatter(x=historico.index, y=historico.values, name="Histórico", line={"color": COR}))
            fig.add_trace(go.Scatter(x=anos_f, y=fc / 1000, name="Projeção", line={"color": COR_SECUNDARIA, "dash": "dash"}))
            emitir(fig)
            texto(f"Projeção 2030: {fc[5]/1000:.2f} Gt. {'Atenção: erro acima de 20%.' if mape > 20 else ''}")

        texto("### Simulador de cenários (todos os países)")
        anos_f = np.arange(ULTIMO_ANO + 1, ULTIMO_ANO + 12)
        hist = matrizes["co2"].loc[ULTIMO_ANO - 10:ULTIMO_ANO]
        x = np.arange(len(hist))
        inclina = hist.apply(lambda col: np.polyfit(x[col.notna().values], col.dropna().values, 1)[0] if col.notna().sum() >= 6 else np.nan)
        validos = inclina.dropna().index
        base = pd.DataFrame({
            iso: np.maximum(matrizes["co2"].loc[ULTIMO_ANO, iso] + inclina[iso] * (anos_f - ULTIMO_ANO), 0)
            for iso in validos
        }, index=anos_f)
        top5 = matrizes["co2"].loc[ULTIMO_ANO, validos].nlargest(5).index
        crescimento = _cagr(
            matrizes["co2"].loc[ULTIMO_ANO - janela_atual, validos],
            matrizes["co2"].loc[ULTIMO_ANO, validos], janela_atual,
        )
        emergentes = [
            iso for iso in validos if iso not in top5
            and crescimento.get(iso, np.nan) >= 0.03
            and matrizes["co2"].loc[ULTIMO_ANO, iso] >= 20
        ]
        cen = base.copy()
        for iso in top5:
            cen[iso] = base[iso] * (1 - reducao / 100) ** (anos_f - ULTIMO_ANO)
        for iso in emergentes:
            share = (matrizes["coal_co2"].loc[ULTIMO_ANO, iso] / matrizes["co2"].loc[ULTIMO_ANO, iso])
            cen[iso] = base[iso] * (1 - troca / 100 * (anos_f - ULTIMO_ANO) / 11 * np.clip(share, 0, 1))
        linha_base, cenario = base.sum(axis=1) / 1000, cen.sum(axis=1) / 1000
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=matrizes["co2"][validos].loc[2000:ULTIMO_ANO].sum(axis=1).index,
                                 y=matrizes["co2"][validos].loc[2000:ULTIMO_ANO].sum(axis=1) / 1000, name="Histórico"))
        fig.add_trace(go.Scatter(x=anos_f, y=linha_base, name="Linha de base", line={"dash": "dash"}))
        fig.add_trace(go.Scatter(x=anos_f, y=cenario, name="Cenário simulado"))
        referencia = 0.55 * matrizes["co2"].loc[2010, validos].sum() / 1000
        fig.add_trace(go.Scatter(x=[2030], y=[referencia], mode="markers", name="Referência aproximada 2030"))
        emitir(fig)
        texto(f"Efeito calculado em 2035: {linha_base.iloc[-1]-cenario.iloc[-1]:.1f} Gt/ano. Referência IPCC é aproximada e deve ser conferida antes de ser citada.")

        texto("### Semáforo de metas")
        _, fim, permitidos, _, _ = obter_contexto(intervalo, conts, bloco, pais_foco)
        variacao = _cagr(
            matrizes["co2"].loc[fim - janela_atual, permitidos],
            matrizes["co2"].loc[fim, permitidos], janela_atual,
        ) * 100
        sem = pd.DataFrame({
            "País": [nomes[i] for i in permitidos],
            "CO₂ (Mt)": matrizes["co2"].loc[fim, permitidos].values,
            "Crescimento a.a. (%)": variacao.values,
        }).dropna()
        sem = sem[sem["CO₂ (Mt)"] >= 5]
        sem["Status"] = np.select(
            [sem["Crescimento a.a. (%)"] <= -1, sem["Crescimento a.a. (%)"] >= 2],
            ["Verde", "Vermelho"], "Amarelo",
        )
        display(sem.sort_values("CO₂ (Mt)", ascending=False).head(30).round(2))
        texto("Limites de referência: verde ≤ −1% a.a.; amarelo entre −1% e +2%; vermelho ≥ +2%.")

    def decisao(intervalo, conts, bloco, pais_foco, janela_atual, volume, crescimento_alto):
        _, fim, permitidos, escopo, iso_foco = obter_contexto(intervalo, conts, bloco, pais_foco)
        inicio = matrizes["co2"].loc[fim - janela_atual, permitidos]
        final = matrizes["co2"].loc[fim, permitidos]
        crescimento = _cagr(inicio, final, janela_atual) * 100
        decisao_df = pd.DataFrame({
            "País": [nomes[i] for i in permitidos], "CO₂ (Mt)": final.values,
            "Crescimento a.a. (%)": crescimento.values,
        }).dropna()
        decisao_df = decisao_df[decisao_df["CO₂ (Mt)"] >= 5]
        total_mundo = mundo["co2"].get(fim, np.nan)
        decisao_df["Participação (%)"] = decisao_df["CO₂ (Mt)"] / total_mundo * 100
        vol = decisao_df["Participação (%)"] >= volume
        cresc = decisao_df["Crescimento a.a. (%)"] >= crescimento_alto
        decisao_df["Grupo"] = np.select(
            [vol & cresc, ~vol & cresc, vol & ~cresc],
            list(GRUPOS_COR)[:3], list(GRUPOS_COR)[3],
        )
        grupo1 = decisao_df[decisao_df["Grupo"] == list(GRUPOS_COR)[0]]
        texto(f"### Matriz de priorização: {len(grupo1)} países no Grupo 1, {grupo1['Participação (%)'].sum():.1f}% das emissões globais.")
        emitir(px.scatter(
            decisao_df, x="CO₂ (Mt)", y="Crescimento a.a. (%)", color="Grupo",
            size="Participação (%)", hover_name="País", log_x=True, size_max=42,
            color_discrete_map=GRUPOS_COR,
        ))
        display(decisao_df.sort_values(["Grupo", "CO₂ (Mt)"], ascending=[True, False]).round(2))

        if not escopo:
            texto("Nenhum país disponível para recomendações.")
            return
        if iso_foco in isos:
            alvo = [iso_foco]
            nome_alvo = nomes[iso_foco]
        else:
            alvo = escopo
            nome_alvo = "seleção atual"
        ini_alvo = soma(matrizes["co2"], alvo).get(fim - janela_atual, np.nan)
        fim_alvo = soma(matrizes["co2"], alvo).get(fim, np.nan)
        cresc_alvo = (fim_alvo / ini_alvo) ** (1 / janela_atual) - 1 if ini_alvo > 0 and fim_alvo > 0 else np.nan
        part = fim_alvo / total_mundo * 100 if total_mundo > 0 else np.nan
        texto("### Recomendações dinâmicas")
        recomendacoes = []
        if pd.notna(cresc_alvo):
            if part >= volume and cresc_alvo * 100 >= crescimento_alto:
                recomendacoes.append("Contenção imediata: alto volume e crescimento alto; metas de pico com monitoramento.")
            elif part < volume and cresc_alvo * 100 >= crescimento_alto:
                recomendacoes.append("Transição preventiva: apoiar infraestrutura limpa antes da consolidação da matriz fóssil.")
            elif part >= volume:
                recomendacoes.append("Redução sustentada: manter e aprofundar metas absolutas.")
            else:
                recomendacoes.append("Monitoramento: acompanhar a tendência e apoiar desenvolvimento de baixa emissão.")
        carvao_alvo = soma(matrizes["coal_co2"], alvo).get(fim, np.nan)
        share_carvao = carvao_alvo / fim_alvo if fim_alvo > 0 else np.nan
        luc_alvo = soma(matrizes["land_use_change_co2"], alvo).get(fim, np.nan)
        co2_luc_alvo = soma(matrizes["co2_including_luc"], alvo).get(fim, np.nan)
        share_luc = luc_alvo / co2_luc_alvo if co2_luc_alvo > 0 else np.nan
        populacao_alvo = soma(matrizes["population"], alvo).get(fim, np.nan)
        pc_alvo = fim_alvo * 1e6 / populacao_alvo if populacao_alvo > 0 else np.nan
        pc_mundo = mundo.get("co2_per_capita", pd.Series(dtype=float)).get(fim, np.nan)
        ap = _ano_pib(matrizes, fim)
        pib_alvo = soma(matrizes["gdp"], alvo)
        intensidade_alvo = (
            soma(matrizes["co2"], alvo).get(ap, np.nan) * 1e9 / pib_alvo.get(ap, np.nan)
            if pib_alvo.get(ap, 0) > 0 else np.nan
        )
        pib_mundo = matrizes["gdp"].loc[ap, isos].sum(min_count=1)
        co2_mundo_ap = matrizes["co2"].loc[ap, isos].sum(min_count=1)
        intensidade_mundo = co2_mundo_ap * 1e9 / pib_mundo if pib_mundo > 0 else np.nan
        if pd.notna(share_carvao) and share_carvao >= 0.3:
            recomendacoes.append(f"Matriz de carvão: {share_carvao:.0%} do CO₂ vem do carvão; priorizar substituição de fontes fósseis.")
        if pd.notna(share_luc) and share_luc >= 0.4:
            recomendacoes.append(f"Uso da terra: representa {share_luc:.0%} do total incluindo LUC; priorizar conservação e controle do desmatamento.")
        if pd.notna(pc_alvo) and pd.notna(pc_mundo):
            if pc_alvo > 2 * pc_mundo:
                recomendacoes.append(f"Emissões per capita ({pc_alvo:.1f} t/hab) superam 2x a média mundial; adotar metas mais exigentes.")
            elif pc_alvo < 0.5 * pc_mundo:
                recomendacoes.append(f"Emissões per capita ({pc_alvo:.1f} t/hab) abaixo de metade da média; apoiar desenvolvimento com energia limpa.")
        if pd.notna(intensidade_alvo) and pd.notna(intensidade_mundo) and intensidade_alvo > 1.5 * intensidade_mundo:
            recomendacoes.append(f"Intensidade ({intensidade_alvo:.2f} kg CO₂/US$) excede 1,5x a média mundial; priorizar eficiência industrial.")
        pib_inicial = soma(matrizes["gdp"], alvo).get(ap - janela_atual, np.nan)
        pib_final = soma(matrizes["gdp"], alvo).get(ap, np.nan)
        co2_inicial = soma(matrizes["co2"], alvo).get(ap - janela_atual, np.nan)
        co2_final = soma(matrizes["co2"], alvo).get(ap, np.nan)
        if pib_inicial > 0 and pib_final > pib_inicial and co2_inicial > 0 and co2_final < co2_inicial:
            recomendacoes.append(f"Desacoplamento: PIB cresceu e CO₂ caiu entre {ap-janela_atual} e {ap}; compartilhar como referência.")
        texto(f"Escopo de recomendação: **{nome_alvo}**")
        for recomendacao in recomendacoes:
            texto(f"- {recomendacao}")

        pib_cresce = matrizes["gdp"].loc[ap] / matrizes["gdp"].loc[ap - janela_atual] - 1
        co2_cresce = matrizes["co2"].loc[ap] / matrizes["co2"].loc[ap - janela_atual] - 1
        candidatos = pd.DataFrame({
            "País": [nomes[i] for i in isos],
            "PIB (%)": (pib_cresce * 100).values,
            "CO₂ (%)": (co2_cresce * 100).values,
            "PIB per capita": (matrizes["gdp"].loc[ap] / matrizes["population"].loc[ap]).values,
            "CO₂ per capita": matrizes["co2_per_capita"].loc[ap].values,
            "PIB": matrizes["gdp"].loc[ap].values,
        }).replace([np.inf, -np.inf], np.nan).dropna()
        candidatos = candidatos[
            (candidatos["PIB (%)"] > 0) & (candidatos["CO₂ (%)"] < 0) & (candidatos["PIB"] > 5e10)
        ]
        gdp_pc_alvo = (
            soma(matrizes["gdp"], alvo).get(ap, np.nan)
            / soma(matrizes["population"], alvo).get(ap, np.nan)
        )
        if pd.notna(gdp_pc_alvo) and np.isfinite(gdp_pc_alvo) and gdp_pc_alvo > 0:
            candidatos = candidatos[
                (candidatos["PIB per capita"] > 0)
                & ~candidatos["País"].isin([nomes[i] for i in alvo])
            ].copy()
            candidatos["Distância de renda"] = np.abs(
                np.log(candidatos["PIB per capita"] / gdp_pc_alvo)
            )
        else:
            candidatos = candidatos.iloc[0:0]
        texto(f"### Benchmark de desacoplamento (PIB até {ap})")
        if candidatos.empty:
            texto("Nenhuma referência comparável com desacoplamento foi encontrada.")
        else:
            display(candidatos.nsmallest(3, "Distância de renda").drop(columns=["PIB", "Distância de renda"]).round(2))

    entradas = widgets.VBox([
        widgets.HTML("<h3>Filtros globais</h3>"),
        widgets.HBox([anos, janela]),
        widgets.HBox([filtro_continente, widgets.VBox([filtro_bloco, foco, metrica])]),
        widgets.HTML("<small>Dados: Our World in Data / Global Carbon Project. Países exibidos com os nomes originais do dataset. Selecione um país em foco para priorizá-lo nos indicadores.</small>"),
    ])
    comuns = {"intervalo": anos, "conts": filtro_continente, "bloco": filtro_bloco, "pais_foco": foco, "janela_atual": janela}
    out_kpis = widgets.interactive_output(
        kpis, {**comuns, "janela_atual": janela}
    )
    out_visao = widgets.interactive_output(
        visao, {**comuns, "metrica_atual": metrica, "eixo": eixo_scatter}
    )
    out_inflexoes = widgets.interactive_output(
        inflexoes, {
            **comuns, "part_max": detector_part, "co2_min": emissao_min,
            "cresc_min": crescimento_rep, "part_atual_max": part_rep,
        }
    )
    out_matriz = widgets.interactive_output(
        matriz_fontes, {**comuns, "escala": escala_fontes}
    )
    out_previsao = widgets.interactive_output(
        previsao, {
            **comuns, "serie": serie_previsao,
            "reducao": reducao_top5, "troca": troca_carvao,
        }
    )
    out_decisao = widgets.interactive_output(
        decisao, {
            **comuns, "volume": limiar_volume,
            "crescimento_alto": limiar_crescimento,
        }
    )

    controles_inflexao = widgets.VBox([detector_part, emissao_min, crescimento_rep, part_rep, out_inflexoes])
    controles_matriz = widgets.VBox([escala_fontes, eixo_scatter, out_matriz])
    controles_previsao = widgets.VBox([serie_previsao, reducao_top5, troca_carvao, out_previsao])
    controles_decisao = widgets.VBox([limiar_volume, limiar_crescimento, out_decisao])
    abas = widgets.Tab(children=[
        out_visao, controles_inflexao, controles_matriz, controles_previsao, controles_decisao,
    ])
    for indice, titulo in enumerate([
        "1. Histórico e geografia", "2. Pontos de inflexão",
        "3. Matriz e intensidade", "4. Projeções", "5. Tomada de decisão",
    ]):
        abas.set_title(indice, titulo)
    painel = widgets.VBox([
        widgets.HTML("<h2>Emissões globais de CO₂ (1750–2024)</h2>"),
        entradas, out_kpis, abas,
    ])
    return painel


criar_dashboard = tematizar(criar_dashboard)


if __name__ == "__main__":
    display(criar_dashboard())
