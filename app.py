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
    editar_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

# ------------------------------------------------------------
# Configurações iniciais
# ------------------------------------------------------------
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# Se veio ?barcode=... na URL, guarda no session_state["codigo"]
params = st.query_params
if "barcode" in params and params["barcode"]:
    st.session_state["codigo"] = params["barcode"][0]

# Cria tabela no banco (se ainda não existir)
criar_tabela()

# ------------------------------------------------------------
# Cabeçalho: crédito e seleção de mês
# ------------------------------------------------------------
credito_inicial = st.number_input(
    "💰 Crédito disponível", min_value=0.0, value=200.0
)

meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0
)

# ------------------------------------------------------------
# Inicialização de session_state para os campos do formulário
# ------------------------------------------------------------
for campo in ["codigo", "nome", "marca", "fabricante", "categoria",
              "valor_unitario", "quantidade"]:
    if campo not in st.session_state:
        st.session_state[campo] = ""  # string ou zero depois convertido pelo widget

# ------------------------------------------------------------
# Formulário de inserção / busca / cadastro / leitura de câmera
# ------------------------------------------------------------
with st.form("formulario"):
    # ⚙️ Text Input vinculado ao session_state["codigo"]
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

    # 📷 Abre o componente JS para leitura via câmera
    if abrir_camera:
        escanear_codigo_web()
        st.experimental_rerun()  # força novo run para pegar o ?barcode

    # 🔍 Buscar produto na API externa
    if buscar:
        code = st.session_state["codigo"].strip()
        if code:
            info = buscar_produto_por_codigo(code)
            if info:
                st.session_state.update({
                    "nome": info.get("nome", ""),
                    "marca": info.get("marca", ""),
                    "fabricante": info.get("fabricante", ""),
                    "categoria": info.get("categoria", "")
                })
                st.success("✅ Produto preenchido com sucesso!")
            else:
                st.warning("❌ Produto não encontrado na base externa.")
        else:
            st.warning("⚠️ Informe um código de barras para buscar.")

    # 📝 Campos manuais
    st.text_input("📝 Nome do produto", key="nome")
    st.text_input("🏷️ Marca", key="marca")
    st.text_input("🏭 Fabricante", key="fabricante")
    st.text_input("📂 Categoria", key="categoria")
    st.number_input(
        "💵 Valor unitário",
        min_value=0.0, step=0.01,
        key="valor_unitario"
    )
    st.number_input(
        "🔢 Quantidade",
        min_value=1, step=1,
        key="quantidade"
    )

    # ✅ Adicionar no banco local
    if adicionar:
        code = st.session_state["codigo"].strip()
        name = st.session_state["nome"].strip()
        if not code or not name:
            st.warning("⚠️ Código e Nome do produto são obrigatórios.")
        else:
            inserir_produto(
                code,
                st.session_state["nome"],
                st.session_state["marca"],
                st.session_state["fabricante"],
                st.session_state["categoria"],
                st.session_state["valor_unitario"],
                st.session_state["quantidade"],
                date.today().strftime("%Y-%m")
            )
            st.success("✅ Produto adicionado com sucesso!")
            # limpa campos
            for key in ["codigo","nome","marca","fabricante",
                        "categoria","valor_unitario","quantidade"]:
                st.session_state[key] = ""
            st.experimental_rerun()

    # 🌍 Cadastrar na Open Food Facts
    if cadastrar:
        code = st.session_state["codigo"].strip()
        name = st.session_state["nome"].strip()
        if code and name:
            sucesso, msg = cadastrar_produto_off(
                code,
                name,
                st.session_state["marca"],
                st.session_state["categoria"]
            )
            if sucesso:
                st.success("✅ " + msg)
            else:
                st.error("❌ " + msg)
        else:
            st.warning("⚠️ Para cadastrar, informe código e nome.")

    # 🧹 Limpar formulário
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for key in ["codigo","nome","marca","fabricante",
                    "categoria","valor_unitario","quantidade"]:
            st.session_state[key] = ""
        st.experimental_rerun()

# ------------------------------------------------------------
# Seção de exibição, exclusão e edição de produtos
# ------------------------------------------------------------
if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("multiple", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        dados,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300,
    )

    selecionados = grid_response.get("selected_rows", [])
    # exclui linhas com _selected_: eles vêm duplicados
    selecionados = [row for row in selecionados if row.get("_selectedRow")]

    # 🚮 Excluir vários produtos
    if selecionados:
        if st.button(f"❌ Excluir {len(selecionados)} produto(s)"):
            for row in selecionados:
                excluir_produto(row["id"])
            st.success("Produtos excluídos.")
            st.experimental_rerun()

    # ✏️ Editar um único produto
    if len(selecionados) == 1:
        prod = selecionados[0]
        with st.expander("✏️ Editar produto selecionado"):
            novo_nome = st.text_input("Nome", value=prod["nome"], key="edit_nome")
            nova_marca = st.text_input("Marca", value=prod["marca"], key="edit_marca")
            novo_fab   = st.text_input("Fabricante", value=prod["fabricante"], key="edit_fab")
            nova_cat   = st.text_input("Categoria", value=prod["categoria"], key="edit_cat")
            novo_val   = st.number_input("Valor unitário", value=float(prod["valor_unitario"]), min_value=0.0, key="edit_val")
            nova_qtd   = st.number_input("Quantidade", value=int(prod["quantidade"]), min_value=1, key="edit_qtd")
            if st.button("💾 Salvar alterações"):
                editar_produto(
                    prod["id"],
                    novo_nome, nova_marca, novo_fab, nova_cat,
                    novo_val, nova_qtd
                )
                st.success("Produto atualizado.")
                st.experimental_rerun()

    # Totais e botões de exportar/limpar
    total, qtd = calcular_totais(dados)
    restante = credito_inicial - total
    st.markdown(f"**Total gasto:** R$ {total:.2f}  |  **Itens:** {qtd}  |  **Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Você ultrapassou seu crédito!")

    cols = st.columns(3)
    with cols[0]:
        csv_bytes = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_bytes, file_name="compras.csv")
    with cols[1]:
        xlsx_bytes = exportar_excel(dados)
        st.download_button("📥 Exportar Excel", data=xlsx_bytes, file_name="compras.xlsx")
    with cols[2]:
        if st.button("🗑️ Limpar este mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.experimental_rerun()

# ------------------------------------------------------------
# Gráfico comparativo
# ------------------------------------------------------------
st.subheader("📊 Comparativo de gastos por mês")
df_res = resumo_mensal()
if df_res.empty:
    st.info("Nenhum dado para mostrar.")
else:
    chart = alt.Chart(df_res).transform_fold(
        ["total_gasto","total_itens"],
        as_=["Tipo","Valor"]
    ).mark_bar().encode(
        x="mes:N",
        y="Valor:Q",
        color="Tipo:N",
        column=alt.Column("Tipo:N", title=None)
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
