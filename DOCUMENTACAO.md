# Documentação do dashboard de emissões de CO₂

## 1. Objetivo do projeto

Este projeto transforma dados históricos de emissões de CO₂ em um dashboard
interativo. A ideia é permitir que uma pessoa explore perguntas como:

- Como as emissões mudaram ao longo do tempo?
- Quais países emitem mais atualmente ou acumularam mais emissões?
- Como as emissões se comparam com a população e o PIB?
- Quais países estão aumentando ou reduzindo suas emissões?
- Como alguns cenários simples poderiam alterar as emissões futuras?

Fizemos o dashboard porque uma tabela CSV grande é difícil de explorar
manualmente. Com filtros, gráficos e indicadores, é possível mudar o recorte da
análise e observar os resultados sem editar o código a cada pergunta.

O painel não tenta substituir uma análise científica ou uma política climática.
Ele reúne indicadores e modelos simplificados para apoiar a exploração dos
dados e a apresentação do trabalho.

## 2. Visão geral: como os arquivos trabalham juntos

O projeto foi separado em módulos para que cada arquivo tenha uma
responsabilidade principal:

| Arquivo | Responsabilidade |
| --- | --- |
| [`dados_co2.py`](./dados_co2.py) | Lê o CSV, seleciona as colunas utilizadas e organiza os dados. |
| [`indicadores_co2.py`](./indicadores_co2.py) | Calcula indicadores, projeções, cenários e recomendações. |
| [`tema_co2.py`](./tema_co2.py) | Define as cores, o estilo dos gráficos e o CSS do painel. |
| [`dashboard_colab.py`](./dashboard_colab.py) | Cria os filtros, gráficos, tabelas, abas e cartões de KPI. |
| [`dashboard_co2_colab.ipynb`](./dashboard_co2_colab.ipynb) | Inicia o dashboard em um notebook Jupyter ou Colab. |
| [`dashboard_co2_colab.py`](./dashboard_co2_colab.py) | Mantém um nome de entrada compatível com versões anteriores do projeto. |
| [`requirements.txt`](./requirements.txt) | Lista as bibliotecas e versões mínimas para instalar o projeto. |

O fluxo principal é:

1. O notebook importa `criar_dashboard` de `dashboard_colab.py`.
2. `criar_dashboard` chama `ler_dados`, que procura o CSV local ou baixa os
   dados da Our World in Data.
3. O módulo de dados transforma o conteúdo em tabelas organizadas por ano e
   país.
4. Os filtros do usuário definem o período, a região, o bloco e o país em foco.
5. `indicadores_co2.py` calcula os números necessários para cada visualização.
6. `dashboard_colab.py` apresenta os resultados com widgets, gráficos e
   tabelas.
7. `tema_co2.py` aplica o visual azul-marinho e branco.
8. Voilà executa o notebook e mostra o painel em uma página no navegador.

Essa divisão ajuda a entender e testar o projeto. Por exemplo, uma regra de
cálculo pode ser alterada em `indicadores_co2.py` sem precisar reconstruir a
interface ou mudar o tema.

## 3. Bibliotecas e como elas se encaixam

### Pandas

O Pandas é a biblioteca principal para trabalhar com os dados tabulares.
`dados_co2.py` usa `pandas.read_csv` para ler o arquivo da Our World in Data.
Depois, transforma os registros em matrizes em que as linhas são anos e as
colunas são países. Isso facilita operações como:

- selecionar as emissões de um ano;
- somar vários países;
- comparar períodos;
- ordenar países por emissão;
- calcular tabelas para os gráficos.

Em outras palavras, o Pandas organiza os dados e permite fazer consultas sobre
eles sem percorrer manualmente cada linha do arquivo.

### NumPy

O NumPy fornece operações numéricas usadas nos cálculos e modelos. No projeto,
ele ajuda a:

- fazer cálculos de tendências e regressões;
- tratar valores ausentes e valores inválidos;
- limitar valores de cenários;
- criar sequências de anos projetados;
- calcular medidas de erro dos modelos.

Pandas e NumPy trabalham juntos: o Pandas mantém os dados identificados por ano
e país, enquanto o NumPy é usado em cálculos numéricos e arrays.

### Plotly

Plotly transforma os dados preparados em gráficos interativos. O usuário pode,
por exemplo, passar o cursor para ver detalhes e usar os controles do gráfico
para aproximar ou explorar uma região.

O código usa duas partes do Plotly:

- `plotly.express` (`px`) para gráficos comuns, como linhas, áreas, barras,
  mapas e dispersões;
- `plotly.graph_objects` (`go`) quando é necessário montar um gráfico com
  várias séries específicas, como histórico, projeção, cenário e faixa de
  incerteza.

`tema_co2.py` aplica cores, fontes, grades e fundos aos gráficos, mas deixa as
séries escolherem suas próprias cores quando isso é importante para diferenciar
os dados.

### ipywidgets

O ipywidgets fornece os controles interativos que aparecem no painel. Entre
eles estão:

- seleção de continente, bloco e país;
- seleção do intervalo de anos e da janela de análise;
- alternância entre emissão total e emissão per capita;
- controles para ajustar limites de crescimento, volume e cenários.

Quando um controle muda, o ipywidgets executa a função associada e atualiza os
resultados. Por isso, não é preciso editar o código nem recarregar manualmente
os dados para experimentar outro filtro.

### Voilà

Voilà é a forma escolhida para apresentar o notebook como uma aplicação web.
Ele executa o notebook no servidor e mostra o resultado no navegador, incluindo
os widgets e os gráficos.

Voilà não substitui Pandas, Plotly ou ipywidgets. Ele é a camada que publica e
apresenta a interface que essas bibliotecas ajudam a construir.

### statsmodels

O `statsmodels` é usado em `indicadores_co2.py` para o modelo de suavização
exponencial de Holt com tendência amortecida. Esse é um dos modelos
comparados para gerar projeções.

O código também avalia tendências linear e drift com os 15 anos mais recentes.
Os três modelos são comparados com um backtest nos anos de 2015 a 2024, e o
modelo com menor MAPE (erro percentual absoluto médio) é escolhido para a
projeção.

### Jinja2

O Jinja2 permite que o Pandas monte as tabelas formatadas usadas no painel.
Por isso, ele aparece como dependência explícita no `requirements.txt`.

### IPython

`IPython.display` permite inserir conteúdo HTML e exibir as figuras dentro do
notebook. O dashboard usa essa funcionalidade para apresentar:

- os cartões de KPI e de recomendação;
- títulos e notas;
- tabelas formatadas;
- gráficos do Plotly.

O CSS do tema estiliza esse conteúdo HTML junto com os widgets.

### ipykernel

O ipykernel executa as células Python do notebook. O Voilà usa esse kernel para
montar o dashboard antes de exibi-lo no navegador.

### Bibliotecas padrão do Python

Alguns recursos usados no projeto já vêm com o Python e não precisam ser
instalados separadamente:

- `dataclasses` organiza estruturas como `Dados`, `Previsao` e `Recomendacao`;
- `pathlib` procura o arquivo CSV em caminhos locais;
- `functools` guarda em cache os dados já carregados e evita leituras repetidas;
- `warnings` apresenta avisos quando um modelo não pode ser usado;
- `html` e `re` ajudam a preparar textos inseridos no HTML;
- `urllib.request`, usado no notebook, baixa módulos quando eles não estão
  disponíveis no ambiente do Colab.

## 4. Como os dados são preparados

O conjunto de dados é publicado pela Our World in Data, com emissões do Global
Carbon Project e outras fontes.
`dados_co2.py` tenta encontrar o arquivo nesta ordem geral:

1. no caminho passado para a função `ler_dados`;
2. na pasta atual;
3. na pasta `doc`;
4. em caminhos usados pelo Google Colab.

Se nenhum arquivo local for encontrado, o módulo tenta ler o CSV do catálogo
atual da Our World in Data. A lista de colunas exigidas pelo código foi
conferida com esse CSV em 19/11/2026. O repositório antigo
[`owid/co2-data`](https://github.com/owid/co2-data) informa que seus arquivos
deixaram de ser atualizados e aponta para o novo catálogo.

Depois da leitura, o código seleciona apenas as colunas necessárias, como
emissão total, população, PIB, emissão per capita e emissões por fonte. Também
remove linhas agregadas que não representam países individuais, preservando
os dados agregados do mundo para comparações.

O painel está configurado para analisar até 2024, mesmo que a fonte contenha
anos mais recentes. Esse é o corte adotado nesta versão do projeto. Ao mudá-lo,
também é preciso revisar o backtest, as projeções e os textos que exibem o ano
final.

O arquivo `Dados` mantém:

- `matrizes`: dados organizados por ano e país para cada indicador;
- `mundo`: as linhas agregadas do mundo;
- `nomes`: a relação entre os códigos dos países e seus nomes;
- `continentes`: a classificação geográfica usada nos filtros.

O dataset não fornece a classificação de continente utilizada pelo painel.
Por isso, as listas de códigos de países por continente e por bloco estão
definidas manualmente em `dados_co2.py`. Países não encontrados nessas listas
recebem a classificação “Outros”, que não é uma opção separada no filtro.

## 5. Como os indicadores e as visualizações são criados

### Indicadores

`indicadores_co2.py` concentra cálculos que não dependem da interface. Alguns
exemplos são:

- crescimento anual composto entre o início e o fim de um período;
- emissão acumulada ao longo do intervalo selecionado;
- classificação de países em grupos de prioridade;
- semáforo de tendência;
- recomendações baseadas em volume, crescimento, carvão, uso da terra e
  emissão per capita;
- comparação com economias que aumentaram o PIB e reduziram as emissões;
- projeções e cenários hipotéticos.

Manter esses cálculos fora do dashboard deixa mais claro o que é regra de
análise e o que é apenas apresentação na tela.

### Interface

`dashboard_colab.py` monta os filtros globais, os controles de cada aba e as
funções que produzem os resultados. Os filtros globais são compartilhados
pelas cinco áreas:

1. **Visão geral:** histórico, mapa, ranking e relação entre emissões, PIB e
   população.
2. **Pontos de inflexão:** países com aceleração das emissões, análise de
   períodos de boom industrial e crescimento atual.
3. **Matriz e intensidade:** composição por fonte, desacoplamento entre PIB e
   CO₂ e intensidade de carbono.
4. **Projeções:** projeções até 2035 e simulador de cenários.
5. **Decisão:** grupos de prioridade, recomendações e benchmark.

O intervalo de anos e a janela controlam as análises históricas. Continente e
bloco definem o conjunto de países usado nas comparações. O país em foco
prioriza os KPIs e o plano de ação, enquanto o mapa e os rankings continuam
mostrando o conjunto filtrado por continente e bloco. Na aba de projeções, a
série é escolhida em um controle próprio e a previsão usa o corte mais recente
definido em `dados_co2.py`.

Os KPIs do topo resumem o escopo filtrado. Por exemplo, o acumulado usa o
intervalo selecionado e o indicador per capita relaciona as emissões com a
população.

Na aba **Projeções**, o simulador usa os dados de todos os países e a janela
selecionada; os filtros de continente, bloco e país em foco não reduzem esse
conjunto.

### Tema visual

`tema_co2.py` mantém a paleta em um só lugar e gera o CSS aplicado ao painel.
Isso evita repetir as mesmas cores em muitos trechos do código. O tema
estiliza os widgets, os cartões, as tabelas e os gráficos, mantendo o texto
legível sobre o fundo azul-marinho.

## 6. Como executar

O projeto recomenda Python 3.10 ou mais recente. A raiz do repositório contém
um `requirements.txt` com as dependências. No Linux ou macOS, execute:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
voila dashboard_co2_colab.ipynb --no-browser --port 8866
```

No Windows PowerShell, use:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
voila dashboard_co2_colab.ipynb --no-browser --port 8866
```

Depois, abra `http://localhost:8866` no navegador. Não é necessário iniciar o
Jupyter manualmente: o Voilà executa o notebook de entrada. O arquivo
`dashboard_co2_colab.ipynb` importa o módulo do dashboard e chama
`criar_dashboard()`.

O CSV pode ficar em `doc/owid-co2-data.csv`. Se o arquivo não estiver
disponível, o código tenta buscar os dados online. Portanto, essa alternativa
precisa de conexão com a internet.

## 7. Regras e fórmulas principais

Os limites abaixo são escolhas do projeto para organizar a análise. Não são
limites científicos ou metas oficiais, e parte deles pode ser ajustada pelos
controles do dashboard.

### Crescimento e grupos de prioridade

O crescimento anual composto (CAGR) é calculado como
`(emissão_final / emissão_inicial) ** (1 / anos) - 1`. A conta só é válida
quando os dois valores são positivos.

Na aba **Decisão**, os padrões são:

- emissão mínima para entrar em rankings e grupos: 5 Mt;
- participação alta nas emissões mundiais: 2% ou mais;
- crescimento alto: 1% ao ano ou mais.

Volume e crescimento formam quatro grupos: volume alto com crescimento alto
fica em contenção imediata; apenas crescimento alto indica transição
preventiva; apenas volume alto indica redução sustentada; os demais ficam em
monitoramento.

O semáforo usa outras faixas: verde para queda anual de pelo menos 1%,
vermelho para crescimento de 2% ou mais e amarelo entre esses limites. A tabela
mostra no máximo os 30 maiores emissores.

As recomendações usam ainda estes padrões: carvão a partir de 30% das emissões,
uso da terra a partir de 40%, emissão per capita acima de 2 vezes ou abaixo de
metade da média mundial, e intensidade de carbono acima de 1,5 vez a média
mundial.

A recomendação de mobilização estima o CO₂ evitado ao reduzir 1% ao ano durante
dez anos. Ela compara essa redução composta com a hipótese simplificada de que
a emissão anual atual permaneceria constante.

### Projeções e simulador

Para a projeção, o código compara tendência linear, drift e Holt amortecido.
Os modelos são treinados com os dados anteriores ao período de teste e
comparados nos dez anos de 2015 a 2024. O MAPE do backtest escolhe o modelo
exibido; depois, o modelo é ajustado à série completa até 2024 para projetar
2025–2035.

A faixa exibida é uma heurística calculada com o RMSE do backtest:
`1,28 × RMSE × raiz(horizonte / 5)`. Ela não é um intervalo estatístico com
cobertura garantida de 80%.

No simulador, a linha de base prolonga linearmente a tendência dos últimos dez
anos. No cenário inicial, os cinco maiores emissores reduzem 3% ao ano. Outros
países entram no grupo de industrialização rápida quando crescem pelo menos 3%
ao ano e emitem pelo menos 20 Mt; nesses países, a substituição do carvão
aumenta gradualmente até 30% em 2035. Os sliders permitem mudar as taxas.

O ponto de referência de 2030 usa 55% do CO₂ fóssil observado em 2010. É uma
comparação simplificada inspirada no IPCC SR1.5, não a reprodução da meta
oficial: o IPCC trata de emissões globais líquidas de CO₂, enquanto o simulador
usa o indicador de CO₂ fóssil desta base de dados.

## 8. Fontes e atualização dos dados

- **Dataset:** [Our World in Data — CO₂ and greenhouse gas emissions](https://catalog.ourworldindata.org/emissions/owid_co2/readme.md).
- **CSV usado como fallback pelo código:** [download do catálogo OWID](https://catalog.ourworldindata.org/emissions/owid_co2/owid_co2.csv).
- **Codebook:** [descrições das colunas](https://catalog.ourworldindata.org/emissions/owid_co2/owid_co2.codebook.csv).
- **Crédito indicado pela fonte:** Global Carbon Budget (2026) e outras fontes, com processamento principal da Our World in Data.
- **Referência climática:** [IPCC, Special Report on Global Warming of 1.5°C](https://www.ipcc.ch/sr15/), em especial o Summary for Policymakers, seção C.1.
- **Summary for Policymakers (PDF):** [relatório oficial](https://www.ipcc.ch/site/assets/uploads/sites/2/2022/06/SPM_version_report_LR.pdf).

O CSV `doc/owid-co2-data.csv` desta cópia do repositório foi versionado no Git
em 12/11/2026. Como o arquivo local tem prioridade, ele pode produzir números
diferentes do fallback online. Para repetir uma análise, use a mesma cópia local
e registre o commit ou a data do arquivo. O fallback online aponta para o
catálogo atual e pode mudar com novas publicações da fonte. A fonte e o código
foram conferidos em 19/11/2026.

## 9. Cuidados ao interpretar os resultados

- **Classificação geográfica:** continentes e blocos são mantidos em listas
  manuais e podem precisar de atualização.
- **Projeções:** o modelo selecionado pelo backtest é uma extrapolação
  estatística, não uma previsão garantida do futuro.
- **Faixa de incerteza:** a faixa exibida é aproximada e baseada no erro
  observado no backtest; não deve ser interpretada como certeza estatística
  sobre o resultado futuro.
- **Simulador:** os controles de redução e substituição de carvão representam
  hipóteses simplificadas. O cenário não modela toda a economia, as políticas
  públicas ou as mudanças tecnológicas.
- **Referência de 2030:** o fator usado no simulador é uma aproximação
  relacionada ao IPCC SR1.5. A própria interface avisa que a fonte deve ser
  conferida antes de ser citada.
- **Benchmark:** a comparação depende de PIB, população e emissões disponíveis
  para o mesmo período. Pode não haver países comparáveis para todos os
  filtros.
- **Unidades:** o painel apresenta valores em unidades diferentes conforme o
  indicador, por exemplo Mt, Gt, t/hab e kg/US$. Confira os rótulos do gráfico
  ou da tabela antes de comparar números.

## 10. Resumo para quem está começando

Uma forma simples de lembrar o papel de cada parte é:

- Pandas e NumPy preparam e calculam os dados.
- `indicadores_co2.py` transforma os dados em medidas e regras de análise.
- Plotly desenha os gráficos.
- ipywidgets cria os controles interativos.
- `dashboard_colab.py` conecta os controles aos cálculos e às visualizações.
- `tema_co2.py` define a aparência.
- Voilà publica o notebook como uma página que pode ser aberta no navegador.

