
<div align="center">

  <h1>🌍 EmissaoCO2_AnaliseDados</h1>

  <p>
    Consultoria de dados sobre as emissões de CO₂ no mundo.
  </p>

  <hr width="60%">

  <h2>📊 Explore a Análise de CO₂</h2>

  <p>
    Explore o dashboard interativo com análises históricas,
    indicadores ambientais, filtros e projeções de emissões.
  </p>

  <p>
    <sub>🐍 Python • 🐼 Pandas • Análise de Dados • Business Intelligence</sub>
  </p>

</div>

## Executar o dashboard

Use o Voilà para abrir o painel como uma apresentação interativa em tela cheia:

```bash
python -m pip install numpy pandas plotly ipywidgets statsmodels voila
voila dashboard_co2_colab.ipynb --no-browser --port 8866
```

Abra `http://localhost:8866` no navegador.

O tema está em [`tema_co2.py`](./tema_co2.py). Os dados ficam em [`dados_co2.py`](./dados_co2.py), os cálculos em [`indicadores_co2.py`](./indicadores_co2.py) e a interface em [`dashboard_colab.py`](./dashboard_colab.py). O painel usa `doc/owid-co2-data.csv` quando disponível e, caso contrário, carrega os dados diretamente da Our World in Data.
