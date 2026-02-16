import streamlit as st
import gspread
from datetime import date

@st.cache_resource

def init_connection():
    client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    return client


sh = init_connection().open_by_key(st.secrets["spreadsheet_id"])

st.header("Registro de Gastos")

tab1, tab2 = st.tabs(["Registrar Gasto", "Cadastrar Categoria"])

with tab1:
    with st.form("form_gastos", clear_on_submit=True):
        with st.container():
            st.subheader("Informações do Gasto")
            col1, col2 = st.columns(2)
            
            with col1:
                data = st.date_input("Data do Gasto", value=date.today())
                categoria = st.selectbox("Categoria", options=sh.worksheet("categorias").col_values(1)[1:])
            with col2:
                descricao = st.text_input("Descrição do Gasto")
                valor = st.number_input("Valor do Gasto", min_value=0.0, format="%.2f")
         
        tabela_base = sh.worksheet("base") 
               
        ultima_id = tabela_base.col_values(1)[1:] if tabela_base.col_values(1) else 0
        id = int(ultima_id[-1]) + 1 if ultima_id else 1
        
        if st.form_submit_button("Registrar Gasto"):
            tabela_base.append_row([id, data.strftime("%Y-%m-%d"), categoria, descricao, valor])
            st.success("Gasto registrado com sucesso!")
                
with tab2:
    with st.form("form_categoria", clear_on_submit=True):
        st.subheader("Cadastrar Nova Categoria")
        nova_categoria = st.text_input("Nome da Categoria")
        
        tabela_categorias = sh.worksheet("categorias")        
        categorias_existentes = tabela_categorias.col_values(1)[1:]
        
        if st.form_submit_button("Cadastrar Categoria"):
            if nova_categoria in categorias_existentes:
                st.warning("Essa categoria já existe.")
            elif nova_categoria.strip() == "":
                st.warning("O nome da categoria não pode ser vazio.")
            else:
                tabela_categorias.append_row([nova_categoria])
                st.success("Categoria cadastrada com sucesso!")