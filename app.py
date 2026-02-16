import streamlit as st
import gspread
from datetime import date
from dateutil.relativedelta import relativedelta

@st.cache_resource
def init_connection():
    client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    return client

sh = init_connection().open_by_key(st.secrets["spreadsheet_id"])

st.header("Registro de Gastos")

tab1, tab2 = st.tabs(["Registrar Gasto", "Cadastrar Categoria"])

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