"""Tema executivo (azul-marinho, branco e cinza) para o dashboard de CO₂.

Este módulo só cuida de aparência: paleta, estilo dos gráficos Plotly e CSS.
O layout do painel é montado em dashboard_colab.py.
"""

from __future__ import annotations

import functools
from string import Template

import ipywidgets as widgets

# ----------------------------------------------------------------- paleta única (fonte da verdade)
PALETA = {
    "bg": "#071A33",            # fundo da página
    "surface": "#0D2A4A",       # cartões e gráficos
    "surface2": "#102F54",      # campos, linhas alternadas
    "borda": "#314A68",
    "borda_forte": "#7392B2",
    "texto": "#FFFFFF",
    "texto_suave": "#D9E6F3",
    "acento": "#5AA9F0",        # série principal e destaques
    "alerta": "#FF8A65",        # usado só para risco (grupo 1, alta de emissão)
}
# Contraste mínimo de 3:1 contra PALETA["surface"] (verificado)
SEQUENCIA = ["#5AA9F0", "#A8C8E8", "#3F8ED8", "#8FA3B8", "#E6EEF7", "#2F7FC1", "#C7D5E4", "#6B8CAE"]
ESCALA = [[0, "#2F7FC1"], [0.5, "#A8C8E8"], [1, "#FFFFFF"]]
COR = PALETA["acento"]
COR_AREA = "rgba(90,169,240,0.25)"
COR_BANDA = "rgba(90,169,240,0.18)"
COR_APOIO = "#8FA3B8"
COR_DESTAQUE = "#E6EEF7"
COR_GRUPO = ["#FF8A65", "#F5C26B", "#5AA9F0", "#8FA3B8"]  # mesma ordem de indicadores_co2.GRUPOS
COR_SITUACAO = {
    "Desacoplamento absoluto": "#5AA9F0",
    "Desacoplamento relativo": "#8FA3B8",
    "Acoplado": "#FF8A65",
}
ESTILO_STATUS = {
    "Verde": "background-color:#1F7A5C;color:#FFFFFF;font-weight:700;text-align:center",
    "Amarelo": "background-color:#F5C26B;color:#071A33;font-weight:700;text-align:center",
    "Vermelho": "background-color:#C8553D;color:#FFFFFF;font-weight:700;text-align:center",
}
FONTE = "Manrope, 'Segoe UI', system-ui, -apple-system, sans-serif"


def formatar_figura(fig, altura: int = 420):
    """Aplica o tema a um gráfico Plotly. Nunca força a cor das séries: quem cria o gráfico escolhe."""
    eixo = {
        "showgrid": True, "gridcolor": PALETA["borda"], "gridwidth": 1,
        "zerolinecolor": PALETA["borda_forte"], "showline": True, "mirror": True,
        "linecolor": PALETA["borda_forte"], "linewidth": 1, "ticks": "outside",
        "tickcolor": PALETA["borda_forte"],
        "tickfont": {"color": PALETA["texto_suave"], "size": 12},
        "title_font": {"color": PALETA["texto"], "size": 12},
    }
    fig.update_layout(
        template="plotly_white", height=altura, margin={"l": 10, "r": 10, "t": 35, "b": 10},
        font={"family": FONTE, "color": PALETA["texto"], "size": 13},
        paper_bgcolor=PALETA["surface"], plot_bgcolor=PALETA["surface"],
        colorway=SEQUENCIA, xaxis=eixo, yaxis=eixo,
        legend={"title_text": "", "bgcolor": "rgba(13,42,74,0.92)", "font": {"color": PALETA["texto"]}},
        hoverlabel={"bgcolor": PALETA["bg"], "bordercolor": PALETA["borda_forte"],
                    "font": {"color": PALETA["texto"], "family": FONTE}},
    )
    fig.update_coloraxes(colorscale=ESCALA, colorbar={
        "outlinewidth": 0, "thickness": 12, "tickfont": {"color": PALETA["texto"]}})
    fig.update_geos(bgcolor="rgba(0,0,0,0)", landcolor="#E6EEF7", countrycolor=PALETA["surface"],
                    coastlinecolor=PALETA["borda_forte"], showocean=False, showlakes=False, showframe=False)
    fig.update_traces(marker={"line": {"width": 0.6, "color": PALETA["surface"]}}, selector={"mode": "markers"})
    fig.update_traces(line_width=2.5, selector={"mode": "lines"})  # só a espessura; a cor fica com o autor
    fig.update_annotations(font={"size": 11, "color": PALETA["texto_suave"]})
    return fig


# As cores entram no CSS pelas variáveis --bg, --surface… (um só lugar para mudar o tema).
CSS_VARIAVEIS = Template("""
.co2-app{--bg:$bg;--surface:$surface;--surface-2:$surface2;--borda:$borda;--borda-forte:$borda_forte;
 --texto:$texto;--texto-suave:$texto_suave;--acento:$acento;--alerta:$alerta;
 --jp-widgets-font-size:14px;--jp-widgets-color:$texto;--jp-widgets-label-color:$texto_suave;
 --jp-widgets-readout-color:$texto;--jp-widgets-slider-active-handle-color:$acento;
 --jp-widgets-slider-handle-border-color:$texto;--jp-widgets-slider-handle-background-color:$surface2;
 --jp-widgets-input-color:$texto;--jp-widgets-input-background-color:$surface2;
 --jp-widgets-input-border-color:$borda_forte;--jp-widgets-input-focus-border-color:$acento}
""")

CSS_REGRAS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
.co2-app{font-family:Manrope,'Segoe UI',system-ui,sans-serif;color:var(--texto);background:var(--bg);
 padding:24px;border-radius:18px;width:100%;box-sizing:border-box}
.co2-app button,.co2-app select,.co2-app input,.co2-app label,.co2-app li{font-family:inherit!important}

/* topo: título + cartões de KPI */
.co2-topo{background:linear-gradient(135deg,var(--bg) 0%,var(--surface-2) 100%);border:1px solid var(--borda);
 border-radius:16px;margin:0 0 18px!important;box-shadow:0 14px 34px rgba(0,10,28,.28)}
.co2-hero{padding:26px 32px 4px!important;margin:0!important}
.co2-hero h1{margin:0 0 6px;font-size:30px;font-weight:800;letter-spacing:-.02em;color:var(--texto)}
.co2-hero p{margin:0;font-size:14px;color:var(--texto-suave)}
.co2-eyebrow{display:inline-block;margin-right:10px;color:var(--acento);font-size:11px;font-weight:800;
 letter-spacing:.12em;text-transform:uppercase}
.co2-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;padding:18px 24px 22px}
.co2-kpi{background:rgba(255,255,255,.05);border:1px solid var(--borda);border-radius:14px;padding:14px 18px}
.co2-kpi-rotulo{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--texto-suave)}
.co2-kpi-valor{margin-top:6px;font-size:26px;font-weight:800;line-height:1.15;overflow-wrap:anywhere;
 font-variant-numeric:tabular-nums}
.co2-kpi-ctx{margin-top:3px;font-size:12px;color:var(--texto-suave)}
.co2-up{color:var(--alerta)}.co2-down{color:var(--acento)}

/* títulos e notas dentro das abas */
.co2-titulo{margin:24px 0 12px;padding-bottom:10px;border-bottom:1px solid var(--borda);font-size:19px;
 font-weight:700;letter-spacing:-.01em;color:var(--texto)}
.co2-subtitulo{margin:18px 0 8px;font-size:15px;font-weight:700;color:var(--texto-suave)}
.co2-nota{margin:8px 0 14px;padding:10px 14px;border-left:4px solid var(--acento);border-radius:8px;
 background:var(--surface-2);font-size:14px;line-height:1.5;color:var(--texto)}
.co2-vazio{padding:22px;border:1px dashed var(--borda-forte);border-radius:12px;color:var(--texto-suave)}

/* cartões de recomendação */
.co2-recs{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin:6px 0 18px}
.co2-rec{padding:14px 16px;border:1px solid var(--borda);border-left:5px solid var(--borda-forte);
 border-radius:12px;background:var(--surface);font-size:14px;line-height:1.5}
.co2-rec-titulo{margin-bottom:6px;font-size:13px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
.co2-rec--alerta{border-left-color:var(--alerta)}.co2-rec--alerta .co2-rec-titulo{color:var(--alerta)}
.co2-rec--atencao{border-left-color:#F5C26B}.co2-rec--atencao .co2-rec-titulo{color:#F5C26B}
.co2-rec--ok{border-left-color:var(--acento)}.co2-rec--ok .co2-rec-titulo{color:var(--acento)}
.co2-rec--info{border-left-color:#8FA3B8}.co2-rec--info .co2-rec-titulo{color:#A8C8E8}

/* filtros globais */
.co2-filtros{background:linear-gradient(145deg,var(--surface),var(--surface-2));border:1px solid var(--borda);
 border-radius:16px;padding:18px 24px!important;margin:0 0 18px!important;box-shadow:0 10px 28px rgba(0,10,28,.20)}
.co2-filtros h3{margin:0 0 12px;font-size:16px;font-weight:700;color:var(--texto)}
.co2-filtros small{display:block;margin-top:12px;font-size:12px;line-height:1.5;color:var(--texto-suave)}
.co2-app .widget-label,.co2-app .widget-inline-hbox .widget-label{text-align:left!important;
 color:var(--texto-suave)!important;font-weight:600;font-size:13px;overflow:visible!important;text-overflow:clip!important}
.co2-rotulo{margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
 color:var(--texto-suave)}

/* campos (select nativo; só dropdowns comuns, nunca select múltiplo) */
.co2-app select{height:40px!important;border:1px solid var(--borda-forte)!important;border-radius:999px!important;
 background-color:var(--surface-2);background-position:right 14px center!important;color:var(--texto);
 padding:0 38px 0 16px;font-size:14px;transition:all .18s ease}
.co2-app select:focus,.co2-app button:focus-visible{outline:2px solid var(--acento);outline-offset:2px}
.co2-app option:checked{background:var(--acento) linear-gradient(0deg,var(--acento),var(--acento));color:var(--bg);font-weight:700}
/* slider: ipywidgets 8 usa noUiSlider; Colab/ipywidgets 7 usa jQuery UI */
.co2-app .noUi-connect,.co2-app .ui-slider-range{background:var(--acento)!important}

.co2-app .widget-toggle-buttons .jupyter-button{height:34px!important;line-height:32px!important;
 padding:0 16px!important;margin:0 6px 6px 0!important;background:var(--surface-2)!important;
 color:var(--texto-suave)!important;border:1px solid var(--borda-forte)!important;border-radius:999px!important;
 box-shadow:none!important;font-weight:600;font-size:13px}
.co2-app .widget-toggle-buttons .jupyter-button:hover{background:var(--borda)!important;color:var(--texto)!important}
.co2-app .widget-toggle-buttons .jupyter-button.mod-active{background:var(--acento)!important;
 color:var(--bg)!important;border-color:var(--acento)!important}

/* abas (as classes mudam entre ipywidgets 7 e 8, por isso [class*=...]) */
.co2-abas>div:first-child{background:transparent!important;border:0!important;margin-bottom:12px}
.co2-abas [class*="TabBar-content"]{gap:8px;border:0!important}
.co2-abas li[class*="TabBar-tab"]{flex:0 0 auto!important;min-width:max-content!important;height:auto!important;
 line-height:1.2!important;padding:10px 20px!important;margin:0!important;top:0!important;transform:none!important;
 background:var(--surface-2)!important;color:var(--texto-suave)!important;border:1px solid var(--borda)!important;
 border-radius:999px!important;font-weight:600;font-size:14px}
.co2-abas li[class*="TabBar-tab"]:before,.co2-abas li[class*="TabBar-tab"]:after{display:none!important}
.co2-abas li[class*="TabBar-tab"]:hover{background:var(--borda)!important;color:var(--texto)!important}
.co2-abas li[class*="TabBar-tab"][class*="mod-current"]{background:var(--acento)!important;color:var(--bg)!important;
 border-color:var(--acento)!important}
.co2-abas .widget-tab-contents{background:transparent!important;border:0!important;padding:4px 0 0!important}

/* painel de controles à esquerda de cada aba */
.co2-controles{background:var(--surface);border:1px solid var(--borda);border-radius:14px;padding:16px!important;
 align-self:start}
.co2-controles .widget-readout{color:var(--texto)!important}

/* gráficos e tabelas */
.co2-app :has(>:is(.js-plotly-plot,.plotly-graph-div)){background:linear-gradient(145deg,var(--surface),var(--surface-2));
 border:1px solid var(--borda);border-radius:16px;padding:12px 16px 6px;margin:0 0 18px;box-sizing:border-box;
 box-shadow:0 12px 30px rgba(0,10,28,.22)}
.co2-app table.dataframe{width:100%;margin:0 0 18px;border:1px solid var(--borda)!important;
 border-collapse:separate!important;border-spacing:0;border-radius:14px;background:var(--surface);
 font-size:13px;font-variant-numeric:tabular-nums}
.co2-app table.dataframe thead th{background:var(--bg)!important;color:var(--texto)!important;font-weight:700;
 text-align:left!important;padding:10px 12px!important;border:0!important}
.co2-app table.dataframe tbody th,.co2-app table.dataframe td{padding:9px 12px!important;border:0!important;
 border-bottom:1px solid var(--borda)!important;background:var(--surface);color:var(--texto)}
.co2-app table.dataframe td{text-align:right}
.co2-app table.dataframe tbody tr:nth-child(even)>*{background:var(--surface-2)}
.co2-app table.dataframe tbody tr:hover>*{background:var(--borda)}
.co2-app table.dataframe tbody tr:last-child>*{border-bottom:0!important}

@media(max-width:900px){
 .co2-aba,.co2-par{grid-template-columns:minmax(0,1fr)!important}
 .co2-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
 .co2-hero{padding:22px 20px 4px!important}}
"""


def css() -> str:
    """CSS completo do tema, com as cores vindas de PALETA."""
    return CSS_VARIAVEIS.substitute(PALETA) + CSS_REGRAS


def tematizar(funcao):
    """Decorador: aplica o tema ao painel devolvido por `funcao` sem mexer no layout dele."""
    @functools.wraps(funcao)
    def envolvida(*args, **kwargs):
        painel = funcao(*args, **kwargs)
        painel.add_class("co2-app")
        estilo = widgets.HTML(f"<style>{css()}</style>", layout=widgets.Layout(display="none"))
        painel.children = (estilo, *painel.children)
        return painel

    return envolvida
