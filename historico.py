import streamlit as st
import pandas as pd
from db import listar_produtos

st.set_page_config(page_title="Histórico de Compras", layout="wide")
st.title("📚 Histórico Completo de Compras")

df = listar_produtos()

col1, col2, col3 = st.columns(3)

with col1:
    busca = st.text_input("🔍 Buscar nome do produto")

with col2:
    categorias = df["categoria"].dropna().unique().tolist()
    filtro_categoria = st.selectbox("📂 Filtrar por categoria", options=["Todas"] + categorias)

with col3:
    datas = df["data"].dropna().unique().tolist()
    filtro_data = st.selectbox("📅 Filtrar por mês", options=["Todas"] + sorted(datas, reverse=True))

if busca:
    df = df[df["nome"].str.contains(busca, case=False)]

if filtro_categoria != "Todas":
    df = df[df["categoria"] == filtro_categoria]

if filtro_data != "Todas":
    df = df[df["data"] == filtro_data]

st.markdown(f"**Total de registros encontrados:** {len(df)}")
st.dataframe(df, use_container_width=True)
