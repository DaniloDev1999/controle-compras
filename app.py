# app.py
import streamlit as st
import altair as alt
import pandas as pd
from datetime import date

from db import (
    criar_tabela,
    inserir_produto,
    listar_meses,
    listar_por_mes,
    limpar_mes,
    resumo_mensal,
    excluir_produto,
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from barcode_web import escanear_codigo_web
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# ───────────────────────────────────────────────────────────────────────────────
# 1) Page setup
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# 2) If we were redirected here with ?barcode=XYZ, stash it immediately
params = st.query_params
if "barcode" in params:
    # take the first value
    st.session_state["codigo"] = params["barcode"][0]

# 3) Ensure every widget key exists in session_state
defaults = {
    "codigo": "",
    "nome": "",
    "marca": "",
    "fabricante": "",
    "categoria": "",
    "valor_unitario": 0.0,
    "quantidade": 1,
    "credito": 200.0,
    "mes": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 4) Initialize DB
criar_tabela()

# 5) Credit and month selector
st.session_state.credito = st.number_input(
    "💰 Crédito disponível",
    min_value=0.0,
    value=st.session_state.credito,
    key="credito",
)
meses = listar_meses()
st.session_state.mes = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0,
    key="mes",
)

# ───────────────────────────────────────────────────────────────────────────────
# 6) Main form
with st.form("formulario"):
    # Bind your barcode text_input directly to session_state["codigo"]
    st.text_input("📦 Código de barras", key="codigo")

    # Action buttons
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
    with c4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")
    with c1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with c2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with c3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    limpar = st.form_submit_button("🧹 Limpar formulário")

    # ── Camera → JS injector → redirect with ?barcode=…
    if abrir_camera:
        escanear_codigo_web()
        st.stop()

    # ── Buscar produto (preserve camera value if user didn’t manually edit)
    if buscar:
        code = st.session_state.codigo.strip()
        if not code:
            st.warning("Por favor, informe um código de barras para buscar.")
        else:
            info = buscar_produto_por_codigo(code)
            if info:
                st.session_state.nome = info.get("nome", "")
                st.session_state.marca = info.get("marca", "")
                st.session_state.fabricante = info.get("fabricante", "")
                st.session_state.categoria = info.get("categoria", "")
                st.success("Produto preenchido com sucesso!")
            else:
                st.warning("Produto não encontrado na base externa.")
        st.experimental_rerun()

    # ── Manual fields, each bound to session_state
    st.text_input("📝 Nome do produto", key="nome")
    st.text_input("🏷️ Marca", key="marca")
    st.text_input("🏭 Fabricante", key="fabricante")
    st.text_input("📂 Categoria", key="categoria")
    st.number_input("💵 Valor unitário", min_value=0.0, step=0.01, key="valor_unitario")
    st.number_input("🔢 Quantidade", min_value=1, step=1, key="quantidade")

    # ── Adicionar ao banco local
    if adicionar:
        code = st.session_state.codigo.strip()
        if not code:
            st.warning("Informe o código de barras antes de adicionar.")
        else:
            inserir_produto(
                code,
                st.session_state.nome,
                st.session_state.marca,
                st.session_state.fabricante,
                st.session_state.categoria,
                st.session_state.valor_unitario,
                st.session_state.quantidade,
                date.today().strftime("%Y-%m"),
            )
            st.success("Produto adicionado com sucesso!")
            # reset all inputs
            for k in ["codigo", "nome", "marca", "fabricante", "categoria"]:
                st.session_state[k] = ""
            st.session_state.valor_unitario = 0.0
            st.session_state.quantidade = 1
            st.experimental_rerun()

    # ── Cadastrar na Open Food Facts
    if cadastrar:
        code = st.session_state.codigo.strip()
        if code and st.session_state.nome.strip():
            ok, msg = cadastrar_produto_off(
                code,
                st.session_state.nome,
                st.session_state.marca,
                st.session_state.categoria,
            )
            st.success(msg) if ok else st.error(msg)
        else:
            st.warning("Código e nome são necessários para cadastrar.")
        st.stop()

    # ── Limpar formulário
    if limpar:
        for k in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[k] = ""
        st.session_state.valor_unitario = 0.0
        st.session_state.quantidade = 1
        st.experimental_rerun()

# ───────────────────────────────────────────────────────────────────────────────
# 7) Quando não estamos no form, mostramos histórico e gráficos

if st.session_state.mes and st.session_state.mes != "Nenhum dado":
    dados = listar_por_mes(st.session_state.mes)
    st.subheader(f"🧾 Produtos de {st.session_state.mes}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("single", use_checkbox=True)
    grid = AgGrid(
        dados,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300,
    )

    sel = grid.get("selected_rows", [])
    with st.expander("🛠️ Ações para produto selecionado"):
        if sel:
            p = sel[0]
            st.markdown(f"""
• **Nome:** `{p['nome']}`  
• **Código:** `{p['codigo']}`  
• **Valor:** R$ {p['valor_unitario']:.2f}  
• **Quantidade:** {p['quantidade']}  
• **Categoria:** `{p['categoria']}`  
• **Data:** `{p['data']}`
""")
            if st.button("❌ Excluir"):
                excluir_produto(p["id"])
                st.experimental_rerun()
        else:
            st.info("Selecione um item acima para ativar ações.")

    total, qtd = calcular_totais(dados)
    restante = st.session_state.credito - total
    st.markdown(
        f"**Total Gasto:** R$ {total:.2f}  \n"
        f"**Itens:** {qtd}  \n"
        f"**Remanescente:** R$ {restante:.2f}"
    )
    if restante < 0:
        st.error("🚨 Crédito ultrapassado!")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "📤 Exportar CSV",
            data=exportar_csv(dados),
            file_name="compras.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "📥 Exportar Excel",
            data=exportar_excel(dados),
            file_name="compras.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c3:
        if st.button("🗑️ Limpar mês"):
            limpar_mes(st.session_state.mes)
            st.experimental_rerun()

st.subheader("📊 Comparativo de gastos entre meses")
df_resumo = resumo_mensal()
if df_resumo.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_resumo)
        .transform_fold(["total_gasto", "total_itens"], as_=["Tipo", "Valor"])
        .mark_bar()
        .encode(
            x="mes:N",
            y="Valor:Q",
            color="Tipo:N",
            column="Tipo:N",
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
