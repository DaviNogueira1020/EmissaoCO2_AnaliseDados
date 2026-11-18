"""Tema azul-marinho, branco e cinza para o dashboard de CO₂ (Jupyter e Colab)."""

import functools
import re

import ipywidgets as widgets
import plotly.express as px

COR = "#0B2545"
COR_SECUNDARIA = "#4F8FCB"
GRUPOS_COR = {
    "Grupo 1 – Contenção imediata": "#0B2545",
    "Grupo 2 – Transição preventiva": "#2F6DB5",
    "Grupo 3 – Redução sustentada": "#8FB4E3",
    "Grupo 4 – Monitoramento": "#A7B0BE",
}
SEQUENCIA = ["#0B2545", "#4F8FCB", "#8A94A6", "#9DB7D5", "#2F6DB5", "#C4CBD6"]
ESCALA = [[0, "#EEF3FA"], [0.25, "#C3D4EA"], [0.5, "#7FA3D1"], [0.75, "#2F5C9E"], [1, "#0B2545"]]
FONTE = "Manrope, 'Segoe UI', system-ui, -apple-system, sans-serif"

px.defaults.color_discrete_sequence = SEQUENCIA


def _formatar(fig, altura=420):
    """Aplica o tema visual aos gráficos mantendo a interface do formatador original."""
    eixo = {
        "showgrid": True,
        "gridcolor": "#E3E8F0",
        "gridwidth": 1,
        "zerolinecolor": "#B8C2D1",
        "showline": True,
        "mirror": True,
        "linecolor": "#B8C2D1",
        "linewidth": 1,
        "ticks": "outside",
        "tickcolor": "#B8C2D1",
        "tickfont": {"color": "#5C6B80", "size": 12},
        "title_font": {"color": "#5C6B80", "size": 12},
    }
    fig.update_layout(
        template="plotly_white",
        height=altura,
        margin={"l": 10, "r": 10, "t": 35, "b": 10},
        font={"family": FONTE, "color": "#1B2B44", "size": 13},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=eixo,
        yaxis=eixo,
        legend={"title_text": "", "bgcolor": "rgba(0,0,0,0)"},
        hoverlabel={
            "bgcolor": "#0B2545",
            "bordercolor": "#0B2545",
            "font": {"color": "#FFFFFF", "family": FONTE},
        },
    )
    fig.update_coloraxes(
        colorscale=ESCALA,
        colorbar={
            "outlinewidth": 0,
            "thickness": 12,
            "tickfont": {"color": "#5C6B80"},
        },
    )
    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        landcolor="#E4E8EF",
        countrycolor="#FFFFFF",
        coastlinecolor="#C9D1DD",
        showocean=False,
        showlakes=False,
    )
    fig.update_traces(
        marker={"line": {"width": 0.6, "color": "#FFFFFF"}},
        selector={"mode": "markers"},
    )
    fig.update_annotations(font={"size": 11, "color": "#5C6B80"})
    return fig


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
.co2-app{--ink:#0B2545;--navy:#13315C;--steel:#5C6B80;--mist:#EEF1F6;--line:#D8DEE8;--paper:#fff;
 --jp-widgets-inline-label-width:150px;--jp-widgets-font-size:14px;
 --jp-widgets-color:#1B2B44;--jp-widgets-label-color:#5C6B80;--jp-widgets-readout-color:#1B2B44;
 --jp-widgets-slider-active-handle-color:#13315C;--jp-widgets-slider-handle-border-color:#13315C;
 --jp-widgets-slider-handle-background-color:#fff;--jp-widgets-input-color:#1B2B44;
 --jp-widgets-input-background-color:#fff;--jp-widgets-input-border-color:#C9D1DD;
 --jp-widgets-input-focus-border-color:#13315C;
 font-family:Manrope,'Segoe UI',system-ui,sans-serif;color:#1B2B44;background:var(--mist);
 padding:20px;border-radius:16px;width:100%;box-sizing:border-box}
.co2-app button,.co2-app select,.co2-app input,.co2-app label,.co2-app li{font-family:inherit!important}

.co2-topo{background:var(--ink);border-radius:14px;overflow:hidden;margin:0 0 16px!important}
.co2-hero{padding:28px 32px 18px!important;margin:0!important}
.co2-hero h1{margin:0 0 6px;font-size:30px;font-weight:800;letter-spacing:-.02em;color:#fff}
.co2-hero p{margin:0;font-size:14px;color:#9FB3CE}
.co2-kpis{margin:0!important;border-top:1px solid rgba(255,255,255,.14)}
.co2-kpis .jp-OutputArea-output{padding:0}
.co2-kpis .widget-hbox{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr));width:100%!important}
.co2-kpis .widget-html{margin:0!important;padding:16px 32px;border-left:1px solid rgba(255,255,255,.14)}
.co2-kpis .widget-html:first-child{border-left:0}
.co2-kpis .widget-html-content{color:#fff;font-size:24px;font-weight:700;line-height:1.2;
 overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.co2-kpis b{display:block;margin-bottom:4px;font-size:13px;font-weight:500;color:#9FB3CE}
.co2-kpis br{display:none}

.co2-app .jp-RenderedHTMLCommon{color:#1B2B44}
.co2-app h3,.co2-app h4{margin:26px 0 14px;padding-bottom:10px;border-bottom:1px solid var(--line);
 color:var(--ink);font-weight:700;letter-spacing:-.01em}
.co2-app h3{font-size:20px}.co2-app h4{font-size:16px}
.co2-filtros{background:var(--paper);border:1px solid var(--line);border-radius:14px;
 padding:18px 22px!important;margin:0 0 16px!important}
.co2-filtros h3{margin:0 0 14px;font-size:16px}
.co2-filtros small{display:block;max-width:70ch;margin-top:8px;font-size:12px;line-height:1.5;color:var(--steel)}
.co2-app .widget-label,.co2-app .widget-inline-hbox .widget-label{text-align:left!important;
 color:var(--steel)!important;font-weight:600;font-size:13px;overflow:visible!important;text-overflow:clip!important}

.co2-app select{height:36px!important;border:1px solid #C9D1DD!important;border-radius:999px!important;
 background-color:#fff;background-position:right 14px center!important;color:#1B2B44;padding:0 36px 0 16px;font-size:14px}
.co2-app select[multiple]{height:auto!important;border-radius:14px!important;padding:6px 8px}
.co2-app select:focus{outline:2px solid rgba(19,49,92,.35);outline-offset:1px;border-color:var(--navy)!important}
.co2-app option:checked{background:var(--navy) linear-gradient(0deg,var(--navy),var(--navy));color:#fff}
.co2-app .noUi-connect,.co2-app .ui-slider-range{background:var(--navy)!important}

.co2-app .widget-toggle-buttons .jupyter-button{height:34px!important;line-height:32px!important;
 padding:0 18px!important;margin:0 6px 0 0!important;background:#fff!important;color:var(--steel)!important;
 border:1px solid #C9D1DD!important;border-radius:999px!important;box-shadow:none!important;
 font-weight:600;font-size:13px}
.co2-app .widget-toggle-buttons .jupyter-button:hover{background:#E8EEF7!important;color:var(--ink)!important}
.co2-app .widget-toggle-buttons .jupyter-button.mod-active{background:var(--navy)!important;
 color:#fff!important;border-color:var(--navy)!important}

.co2-abas>div:first-child{background:transparent!important;border:0!important;margin-bottom:12px}
.co2-abas [class*="TabBar-content"]{gap:8px;border:0!important}
.co2-abas li[class*="TabBar-tab"]{flex:0 0 auto!important;min-width:max-content!important;height:auto!important;
 line-height:1.2!important;padding:10px 20px!important;margin:0!important;top:0!important;transform:none!important;
 background:#fff!important;color:var(--steel)!important;border:1px solid var(--line)!important;
 border-radius:999px!important;font-weight:600;font-size:14px}
.co2-abas li[class*="TabBar-tab"]:before,.co2-abas li[class*="TabBar-tab"]:after{display:none!important}
.co2-abas li[class*="TabBar-tab"]:hover{background:#E8EEF7!important;color:var(--ink)!important}
.co2-abas li[class*="TabBar-tab"]:focus-visible{outline:2px solid var(--navy);outline-offset:2px}
.co2-abas li[class*="TabBar-tab"][class*="mod-current"]{background:var(--navy)!important;color:#fff!important;
 border-color:var(--navy)!important}
.co2-abas .widget-tab-contents{background:transparent!important;border:0!important;padding:4px 0 0!important}

.co2-app :has(>:is(.js-plotly-plot,.plotly-graph-div)){background:var(--paper);border:1px solid var(--line);
 border-radius:14px;padding:10px 14px 4px;margin:0 0 18px;box-sizing:border-box}
.co2-app table.dataframe{width:100%;margin:0 0 18px;border:1px solid var(--line)!important;
 border-collapse:separate!important;border-spacing:0;border-radius:14px;background:#fff;
 font-size:13px;font-variant-numeric:tabular-nums}
.co2-app table.dataframe thead th{background:var(--ink)!important;color:#fff!important;font-weight:600;
 text-align:left!important;padding:10px 12px!important;border:0!important}
.co2-app table.dataframe thead tr:first-child th:first-child{border-top-left-radius:13px}
.co2-app table.dataframe thead tr:first-child th:last-child{border-top-right-radius:13px}
.co2-app table.dataframe tbody th,.co2-app table.dataframe td{padding:8px 12px!important;border:0!important;
 border-bottom:1px solid #E4E8EF!important;background:#fff;color:#1B2B44}
.co2-app table.dataframe tbody th{color:var(--steel)!important;font-weight:500;text-align:left}
.co2-app table.dataframe td{text-align:right}
.co2-app table.dataframe tbody tr:nth-child(even)>*{background:#F5F7FA}
.co2-app table.dataframe tbody tr:hover>*{background:#E8EEF7}
.co2-app table.dataframe tbody tr:last-child>*{border-bottom:0!important}
.co2-app table.dataframe tbody tr:last-child>*:first-child{border-bottom-left-radius:13px}
.co2-app table.dataframe tbody tr:last-child>*:last-child{border-bottom-right-radius:13px}

@media(max-width:760px){
 .co2-kpis .widget-hbox{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .co2-hero{padding:22px 20px 14px!important}.co2-kpis .widget-html{padding:14px 20px}}
"""


def aplicar_tema(painel):
    """Aplica o visual ao painel devolvido por criar_dashboard()."""
    estilo = widgets.HTML(
        f"<style>{CSS}</style>",
        layout=widgets.Layout(display="none"),
    )
    painel.add_class("co2-app")
    try:
        titulo, filtros, kpis, abas = painel.children
    except ValueError:
        painel.children = (estilo, *painel.children)
        return painel

    periodo = re.search(r"\((.*?)\)", titulo.value)
    serie = (
        f"Série histórica de {periodo.group(1).replace('–', ' a ')}. "
        if periodo else ""
    )
    hero = widgets.HTML(
        f"<h1>Emissões globais de CO₂</h1>"
        f"<p>{serie}Fonte: Our World in Data e Global Carbon Project.</p>"
    )
    hero.add_class("co2-hero")
    kpis.add_class("co2-kpis")
    filtros.add_class("co2-filtros")
    abas.add_class("co2-abas")
    try:
        abas.titles = tuple(re.sub(r"^\d+\.\s*", "", titulo) for titulo in abas.titles)
    except AttributeError:
        pass
    topo = widgets.VBox([hero, kpis])
    topo.add_class("co2-topo")
    painel.children = (estilo, topo, filtros, abas)
    return painel


def tematizar(funcao):
    """Aplica o tema ao painel retornado pela função."""
    @functools.wraps(funcao)
    def envolvida(*args, **kwargs):
        return aplicar_tema(funcao(*args, **kwargs))

    return envolvida
