import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

@st.cache_resource
def init_connection():
    client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    return client

sh = init_connection().open_by_key(st.secrets["spreadsheet_id"])

st.header("Registro de Gastos")

tab1, tab2, tab3 = st.tabs(["Registrar Gasto", "Cadastrar Categoria", "Relatórios"])

with tab1:
    ws_cats = sh.worksheet("categorias")
    lista_categorias = ws_cats.col_values(1)[1:]

    with st.form("form_gastos", clear_on_submit=True):
        st.subheader("Informações do Gasto")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            data_inicial = st.date_input("Data do Gasto", value=date.today())
        with col2:
            categoria = st.selectbox("Categoria", options=lista_categorias)
        with col3:
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
        with col4:
            parcelas = st.number_input("Parcelamento", min_value=1, max_value=48, value=1)
            
        descricao = st.text_input("Descrição do Gasto")
        submit = st.form_submit_button("Registrar Gasto")

    if submit:
        tabela_base = sh.worksheet("base")
        
        col_id = tabela_base.col_values(1)
        
        id_base = int(col_id[-1]) + 1 if len(col_id) > 1 else 1
        
        novas_linhas = []

        for i in range(parcelas):
            id_atual = id_base + i
            
            data_parcela = data_inicial + relativedelta(months=i)
            desc_formatada = f"{descricao} ({i+1}/{parcelas})" if parcelas > 1 else descricao
            
            linha = [
                id_atual, 
                data_parcela.strftime("%Y-%m-%d"), 
                categoria, 
                desc_formatada, 
                valor
            ]
            novas_linhas.append(linha)
        
        tabela_base.append_rows(novas_linhas)
        st.success(f"Gasto registrado. IDs gerados: {id_base} até {id_base + parcelas - 1}")

with tab2:
    with st.form("form_categoria", clear_on_submit=True):
        st.subheader("Cadastrar Nova Categoria")
        nova_categoria = st.text_input("Nome da Categoria")
        
        if st.form_submit_button("Cadastrar Categoria"):
            tabela_categorias = sh.worksheet("categorias")        
            categorias_existentes = tabela_categorias.col_values(1)
            
            if nova_categoria in categorias_existentes:
                st.warning("Essa categoria já existe.")
            elif not nova_categoria.strip():
                st.warning("O nome não pode ser vazio.")
            else:
                tabela_categorias.append_row([nova_categoria])
                st.success("Categoria cadastrada!")
                st.rerun()
                
# PROTOTIPO IA - AINDA IREI DESENVOLVER ESSA PARTE
with tab3:
    st.subheader("Análise de Gastos e Faturas")

    # 1. Carregamento e Tratamento (ETL)
    dados_brutos = sh.worksheet("base").get_all_values()

    if len(dados_brutos) > 1:
        # Define cabeçalho e dados
        df = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])

        # Limpeza de Tipos
        # Remove símbolos de moeda caso existam, troca vírgula por ponto e converte
        df["Valor"] = pd.to_numeric(
            df["Valor"].astype(str).str.replace("R$", "", regex=False)
            .str.replace(".", "", regex=False) # Remove separador de milhar se houver
            .str.replace(",", "."), errors="coerce"
        ).fillna(0.0)
        
        df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors="coerce")
        
        # Cria colunas auxiliares apenas para popular os filtros (Selectbox)
        df["Ano"] = df["Data"].dt.year
        df["Mes"] = df["Data"].dt.month

        # 2. Controles de Filtragem
        col_tipo, col_ano, col_mes = st.columns([2, 1, 1])
        
        with col_tipo:
            tipo_periodo = st.radio(
                "Regime de Visualização:", 
                ["Mês Civil (1 a 30/31)", "Fatura Cartão (16 a 15)"],
                horizontal=True
            )
            
        with col_ano:
            # Pega anos únicos ordenados
            anos_disponiveis = sorted(df["Ano"].dropna().unique().astype(int), reverse=True)
            ano_sel = st.selectbox("Ano de Referência", anos_disponiveis)
            
        with col_mes:
            # Meses (fixo de 1 a 12 para facilitar a navegação entre faturas futuras/passadas)
            mes_sel = st.selectbox("Mês de Referência", range(1, 13), index=date.today().month - 1)

        # 3. Lógica de Definição das Datas de Corte
        if tipo_periodo == "Mês Civil (1 a 30/31)":
            # Data Inicial: Dia 1 do mês/ano selecionado
            data_inicio = datetime(ano_sel, mes_sel, 1)
            # Data Final: Último dia do mês (truque: dia 1 do mês seguinte - 1 dia)
            proximo_mes = mes_sel + 1 if mes_sel < 12 else 1
            proximo_ano = ano_sel if mes_sel < 12 else ano_sel + 1
            data_fim = datetime(proximo_ano, proximo_mes, 1) - pd.Timedelta(days=1)
            
        else: # Fatura Cartão (16 a 15)
            # Se a referência é Março (03), a fatura pega de 16/Fev a 15/Mar
            data_fim = datetime(ano_sel, mes_sel, 15)
            
            # Cálculo do mês anterior para o início
            mes_anterior = mes_sel - 1 if mes_sel > 1 else 12
            ano_anterior = ano_sel if mes_sel > 1 else ano_sel - 1
            data_inicio = datetime(ano_anterior, mes_anterior, 16)

        # Exibe o intervalo exato para transparência (User Requirement: Transparência)
        st.caption(f"📅 Filtrando dados de: **{data_inicio.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**")

        # 4. Aplicação do Filtro no DataFrame
        # O método .between inclui os extremos (inclusive=True por padrão)
        mask = df["Data"].between(data_inicio, data_fim)
        df_filtrado = df.loc[mask]

        # 5. Exibição dos Resultados
        if not df_filtrado.empty:
            st.divider()
            
            # Agregação
            resumo = df_filtrado.groupby("Categoria")[["Valor"]].sum().reset_index()
            resumo = resumo.sort_values(by="Valor", ascending=False)
            
            total_periodo = resumo["Valor"].sum()

            col_metrica, col_tabela = st.columns([1, 2])
            
            with col_metrica:
                st.metric(
                    label=f"Total {tipo_periodo.split()[0]}", 
                    value=f"R$ {total_periodo:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                )
                
                # Gráfico Donut (mais limpo para categorias)
                st.altair_chart(
                    pd.DataFrame(resumo), # Placeholder se quiser usar altair, ou use o bar_chart abaixo
                    use_container_width=True
                )
                
            with col_tabela:
                 st.dataframe(
                    resumo,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Categoria": "Categoria",
                        "Valor": st.column_config.NumberColumn(
                            "Gasto (R$)",
                            format="R$ %.2f"
                        )
                    }
                )
            
            # Detalhamento opcional (Drill down)
            with st.expander("Ver Detalhamento dos Lançamentos"):
                st.dataframe(
                    df_filtrado[["Data", "Descrição", "Categoria", "Valor"]].sort_values("Data"),
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                    }
                )

        else:
            st.warning(f"Não há lançamentos registrados entre {data_inicio.strftime('%d/%m')} e {data_fim.strftime('%d/%m')}.")

    else:
        st.info("A base de dados está vazia. Registre alguns gastos na primeira aba.")