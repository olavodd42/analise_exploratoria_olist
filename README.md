# 📦 Análise Exploratória de E-commerce (Olist)

Este projeto realiza uma **Análise Exploratória de Dados (EDA)** com foco em **insights de marketing** utilizando o [Olist Brazilian E-commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

O objetivo principal é **compreender o comportamento dos clientes e identificar oportunidades para estratégias de marketing**, como fidelização, upsell, cross-sell e campanhas de reativação.

---

## 🔹 Estrutura da Análise

1. **Perfil dos Clientes e Ticket Médio por Região**

   * Quantidade de clientes por estado.
   * Ticket médio (faturamento / nº de pedidos) por UF.
   * Identificação das regiões de maior potencial de valor.

2. **Produtos e Categorias**

   * Categorias mais vendidas.
   * Categorias que geram maior faturamento.
   * Comparação entre volume de pedidos e valor agregado.

3. **Entrega x Satisfação (Atraso vs. Review)**

   * Correlação entre atraso de entrega e notas de review.
   * Identificação de gargalos logísticos que impactam satisfação.

4. **RFM Analysis (Recency, Frequency, Monetary)**

   * Segmentação de clientes com base em:

     * Recency: tempo desde a última compra.
     * Frequency: número de pedidos realizados.
     * Monetary: total gasto.
   * Criação de segmentos como **Campeões, Fiéis, Em Risco, Perdidos**.
   * Visualização da distribuição de clientes por segmento.

5. **Dashboard Interativo (Streamlit)**

   * KPIs principais (pedidos, faturamento, ticket médio, % entregas no prazo).
   * Gráficos interativos por **UF, tempo, categorias, reviews e segmentos RFM**.
   * Possibilidade de aplicar filtros (período, estados) e exportar dados em CSV.

6. **Insights Automáticos**

   * Bullet points gerados a partir das métricas (ticket médio, categorias líderes, impacto de atraso em reviews, principais segmentos RFM).

---

## 🔹 Principais Insights

* 🎯 **20% dos clientes concentram a maior parte do faturamento (segmento Campeões)** → oportunidade para programas VIP.
* 🚚 **Atrasos de entrega acima de 7 dias reduzem a nota média de review em \~40%** → impacto direto na satisfação.
* 🛍️ **Categoria "beleza\_saude" lidera em volume, mas com ticket médio baixo** → ideal para cross-sell.
* 📍 **Clientes do Sudeste têm ticket médio maior**, mas o Nordeste apresenta crescimento → oportunidade para expansão regional.
* ⏰ **Clientes em risco representam parcela significativa da base** → campanhas de reativação podem gerar bom retorno.

---

## 🔹 Tecnologias Utilizadas

* **Python 3.10+**
* **Pandas** para manipulação de dados
* **Matplotlib / Seaborn** para visualização
* **Jupyter Notebook** para exploração e storytelling
* **Streamlit** para construção do dashboard interativo

---

## 🔹 Como Reproduzir

1. Clone este repositório:

   ```bash
   git clone https://github.com/seuusuario/olist-eda-marketing.git
   cd olist-eda-marketing
   ```

2. Crie e ative um ambiente virtual (opcional, recomendado):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

4. Baixe o dataset da Olist no [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) e extraia os CSVs dentro da pasta `data/`.

5. Execute as análises no notebook:

   ```bash
   jupyter notebook notebooks/notebook_rfm_enriquecido.ipynb
   ```

6. Execute o dashboard interativo:

   ```bash
   streamlit run app.py
   ```

---

## 🔹 Estrutura do Projeto

```
📦 olist-eda-marketing
 ┣ 📂 data/                  # datasets (não versionados)
 ┣ 📂 notebooks/             # notebooks de análise
 ┣ 📂 outputs/               # gráficos e relatórios gerados
 ┣ 📜 app.py                 # dashboard interativo (Streamlit)
 ┣ 📜 requirements.txt       # dependências
 ┣ 📜 README.md              # este arquivo
```

---

## 🔹 Próximos Passos

* Adicionar mapas interativos por UF (PyDeck ou GeoPandas).
* Implementar modelos preditivos de churn ou propensão de compra usando machine learning.
* Explorar análise de reviews textuais (NLP) para complementar a visão quantitativa.
* Criar testes unitários para funções de pré-processamento de dados.

---

✍️ Autor: **Olavo Defendi Dalberto**
🎓 Engenharia da Computação - UFSM
📌 Projeto pessoal/portfólio em Ciência de Dados
