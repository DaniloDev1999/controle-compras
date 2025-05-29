import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela,
    inserir_produto,
    listar_produtos,
    listar_meses,
    listar_por_mes,
    limpar_mes,
    resumo_mensal,
    excluir_produto,
    editar_produto as db_editar_produto,
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# 0) Se veio ?barcode=... na URL, joga direto em session_state["codigo"]
query_params = st.query_params
if "barcode" in query_params:
    st.session_state["codigo"] = query_params["barcode"][0]

criar_tabela()

# Crédito disponível
credito_inicial = st.number_input("💰 Crédito disponível", min_value=0.0, value=200.0)

# Escolha do mês
meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0
)

# Inicializa chaves de estado
for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
    if campo not in st.session_state:
        st.session_state[campo] = ""

# == FORMULÁRIO ==============================================================
with st.form("formulario"):
    # agora vinculamos o text_input diretamente a st.session_state["codigo"]
    st.text_input("📦 Código de barras", key="codigo")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with col2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with col3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    with col4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # Campos de entrada manual (vinculados a session_state)
    st.text_input("📝 Nome do produto", key="nome")
    st.text_input("🏷️ Marca", key="marca")
    st.text_input("🏭 Fabricante", key="fabricante")
    st.text_input("📂 Categoria", key="categoria")
    valor_unitario = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1)

# == AÇÕES DO FORMULÁRIO (fora do bloco `with`) =============================

# 1) Abrir câmera
if abrir_camera:
    escanear_codigo_web()

# 2) Buscar produto na API externa
if buscar:
    code = st.session_state["codigo"].strip()
    if not code:
        st.warning("Por favor, informe um código de barras para buscar.")
    else:
        info = buscar_produto_por_codigo(code)
        if info:
            st.session_state.update({
                "nome": info.get("nome", ""),
                "marca": info.get("marca", ""),
                "fabricante": info.get("fabricante", ""),
                "categoria": info.get("categoria", ""),
            })
            st.success("Produto preenchido com sucesso!")
        else:
            st.warning("Produto não encontrado na base externa.")

# 3) Adicionar no banco local
if adicionar:
    code = st.session_state["codigo"].strip()
    if not code:
        st.warning("Para adicionar, informe primeiro o código de barras.")
    else:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(
            code,
            st.session_state["nome"],
            st.session_state["marca"],
            st.session_state["fabricante"],
            st.session_state["categoria"],
            valor_unitario,
            quantidade,
            data_hoje
        )
        st.success("Produto adicionado com sucesso!")
        # limpa TODOS os campos do formulário
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[campo] = ""
        st.experimental_rerun()

# 4) Cadastrar na Open Food Facts
if cadastrar:
    code = st.session_state["codigo"].strip()
    if not code:
        st.warning("Para cadastrar, informe primeiro o código de barras.")
    else:
        sucesso, msg = cadastrar_produto_off(
            code,
            st.session_state["nome"],
            st.session_state["marca"],
            st.session_state["categoria"]
        )
        if sucesso:
            st.success(msg)
        else:
            st.error(msg)

# 5) Limpar formulário manualmente
if st.button("🧹 Limpar formulário"):
    for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
        st.session_state[campo] = ""
    st.experimental_rerun()

# == EXIBIÇÃO DO HISTÓRICO MENSAL ===========================================
if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("single", use_checkbox=True)
    grid_response = AgGrid(
        dados,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300
    )

    selected = grid_response.get("selected_rows", [])
    if isinstance(selected, pd.DataFrame):
        selected = selected.to_dict("records")

    with st.expander("🛠️ Ações para produto selecionado"):
        if selected:
            p = selected[0]
            st.markdown(f"""
            ✅ **Produto Selecionado:**
            • **Nome:** `{p['nome']}`  
            • **Código:** `{p['codigo']}`  
            • **Valor Unitário:** R$ {p['valor_unitario']:.2f}  
            • **Quantidade:** {p['quantidade']}  
            • **Categoria:** `{p['categoria']}`  
            • **Data:** `{p['data']}`  
            """)
            if st.button("❌ Excluir Produto Selecionado"):
                excluir_produto(p["id"])
                st.warning("Produto excluído.")
                st.experimental_rerun()
            with st.form("editar_produto"):
                novo_nome       = st.text_input("✏️ Nome", value=p["nome"])
                nova_marca      = st.text_input("🏷️ Marca", value=p.get("marca",""))
                novo_fabricante = st.text_input("🏭 Fabricante", value=p.get("fabricante",""))
                nova_categoria  = st.text_input("📂 Categoria", value=p.get("categoria",""))
                novo_valor      = st.number_input("💵 Valor unitário", value=p["valor_unitario"], min_value=0.0)
                nova_qtd        = st.number_input("🔢 Quantidade", value=p["quantidade"], min_value=1)
                salvar = st.form_submit_button("💾 Salvar Alterações")
                if salvar:
                    db_editar_produto(
                        p["id"],
                        novo_nome,
                        nova_marca,
                        novo_fabricante,
                        nova_categoria,
                        novo_valor,
                        nova_qtd
                    )
                    st.success("Produto atualizado.")
                    st.experimental_rerun()

    total, qtd = calcular_totais(dados)
    restante  = credito_inicial - total
    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Quantidade Total:** {qtd}")
    st.markdown(f"**Valor Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Você ultrapassou seu crédito disponível!")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📤 Exportar CSV", data=exportar_csv(dados), file_name="compras.csv", mime="text/csv")
    with c2:
        st.download_button("📥 Exportar Excel", data=exportar_excel(dados), file_name="compras.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.experimental_rerun()

# == COMPARATIVO ENTRE MESES ===============================================
st.subheader("📊 Comparativo de gastos entre meses")
df_res = resumo_mensal()
if df_res.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_res)
           .transform_fold(["total_gasto", "total_itens"], as_=["Tipo","Valor"])
           .mark_bar()
           .encode(
               x=alt.X("mes:N", title="Mês"),
               y=alt.Y("Valor:Q", title="Valor"),
               color="Tipo:N",
               column=alt.Column("Tipo:N", title=None),
           )
           .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
