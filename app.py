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

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# Inicializa no session_state os valores numéricos, para garantir o tipo correto
if "valor_unitario" not in st.session_state:
    st.session_state["valor_unitario"] = 0.0
if "quantidade" not in st.session_state:
    st.session_state["quantidade"] = 1

# Captura código lido pela câmera via query string
query_params = st.query_params
if "barcode" in query_params:
    st.session_state["codigo"] = query_params["barcode"][0]

criar_tabela()

credito_inicial = st.number_input(
    "💰 Crédito disponível",
    value=200.0,
    min_value=0.0,
    key="credito_inicial"
)

meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0
)

# Inicializa as chaves de texto
for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
    if campo not in st.session_state:
        st.session_state[campo] = ""

with st.form("formulario"):
    # Campo de código de barras (preenchido manual ou pela câmera)
    codigo_input = st.text_input(
        "📦 Código de barras",
        value=st.session_state["codigo"],
        key="codigo_input"
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with col2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with col3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    with col4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # Abre leitor de código na tela
    if abrir_camera:
        escanear_codigo_web()

    # Busca produto na API, preservando código de barras
    if buscar:
        code = codigo_input.strip() or st.session_state["codigo"].strip()
        st.session_state["codigo"] = code
        if code:
            info = buscar_produto_por_codigo(code)
            if info:
                st.session_state["nome"]       = info.get("nome", "")
                st.session_state["marca"]      = info.get("marca", "")
                st.session_state["fabricante"] = info.get("fabricante", "")
                st.session_state["categoria"]  = info.get("categoria", "")
                st.success("Produto preenchido com sucesso!")
            else:
                st.warning("Produto não encontrado na base externa.")
        else:
            st.warning("Por favor, informe um código de barras para buscar.")

    # Campos de preenchimento manual (já pré-populados do session_state)
    nome       = st.text_input("📝 Nome do produto", value=st.session_state["nome"])
    marca      = st.text_input("🏷️ Marca", value=st.session_state["marca"])
    fabricante = st.text_input("🏭 Fabricante", value=st.session_state["fabricante"])
    categoria  = st.text_input("📂 Categoria", value=st.session_state["categoria"])

    # Agora definimos value e key para garantir tipo float/int corretos
    valor_unit = st.number_input(
        "💵 Valor unitário",
        value=st.session_state["valor_unitario"],
        min_value=0.0,
        step=0.01,
        key="valor_unitario"
    )
    quantidade = st.number_input(
        "🔢 Quantidade",
        value=st.session_state["quantidade"],
        min_value=1,
        step=1,
        key="quantidade"
    )

    # Inserção no banco local
    if adicionar and st.session_state["codigo"]:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(
            st.session_state["codigo"],
            nome, marca, fabricante, categoria,
            valor_unit, quantidade, data_hoje
        )
        st.success("Produto adicionado com sucesso!")
        # Limpa campos do formulário
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[campo] = ""
        # Também volta valores numéricos ao default
        st.session_state["valor_unitario"] = 0.0
        st.session_state["quantidade"]     = 1
        st.rerun()

    # Cadastra na Open Food Facts
    if cadastrar and st.session_state["codigo"] and nome:
        sucesso, msg = cadastrar_produto_off(
            st.session_state["codigo"],
            nome, marca, categoria
        )
        if sucesso:
            st.success(msg)
        else:
            st.error(msg)

    # Limpar formulário
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[campo] = ""
        st.session_state["valor_unitario"] = 0.0
        st.session_state["quantidade"]     = 1
        st.rerun()

# ─── Exibição e edição dos produtos do mês ────────────────────────────────────────

if mes_escolhido and mes_escolhido != "Nenhum dado":
    df = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("single", use_checkbox=True)
    grid_resp = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        height=300
    )

    selecionados = grid_resp.get("selected_rows") or []
    if selecionados:
        prod = selecionados[0]
        with st.expander("🛠️ Ações para produto selecionado"):
            st.markdown(f"""
            ✅ **Nome:** `{prod['nome']}`  
            • **Código:** `{prod['codigo']}`  
            • **Valor Unitário:** R$ {float(prod['valor_unitario']):.2f}  
            • **Quantidade:** {int(prod['quantidade'])}  
            • **Categoria:** `{prod['categoria']}`  
            • **Data:** `{prod['data']}`
            """)
            # Excluir
            if st.button("❌ Excluir Produto Selecionado"):
                excluir_produto(prod["id"])
                st.warning("Produto excluído.")
                st.experimental_rerun()

            # Formulário de edição
            with st.form("editar_prod"):
                novo_nome      = st.text_input("✏️ Nome", value=prod["nome"], key="edit_nome")
                nova_marca     = st.text_input("🏷️ Marca", value=prod["marca"], key="edit_marca")
                novo_fabric    = st.text_input("🏭 Fabricante", value=prod["fabricante"], key="edit_fabricante")
                nova_categoria = st.text_input("📂 Categoria", value=prod["categoria"], key="edit_categoria")
                novo_valor     = st.number_input(
                    "💵 Valor unitário",
                    min_value=0.0,
                    step=0.01,
                    value=float(prod["valor_unitario"]),
                    key="edit_valor"
                )
                nova_qtd       = st.number_input(
                    "🔢 Quantidade",
                    min_value=1,
                    step=1,
                    value=int(prod["quantidade"]),
                    key="edit_qtd"
                )
                salvar = st.form_submit_button("💾 Salvar Alterações")
                if salvar:
                    editar_produto(
                        prod["id"],
                        novo_nome, nova_marca, novo_fabric,
                        nova_categoria, novo_valor, nova_qtd
                    )
                    st.success("✅ Produto atualizado.")
                    st.experimental_rerun()

    # Totais e exportação
    total, qtd = calcular_totais(df)
    rest = st.session_state["credito_inicial"] - total

    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Itens no mês:** {qtd}")
    st.markdown(f"**Crédito Restante:** R$ {rest:.2f}")
    if rest < 0:
        st.error("🚨 Crédito ultrapassado!")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📤 Exportar CSV", exportar_csv(df), "compras.csv", "text/csv")
    with c2:
        st.download_button(
            "📥 Exportar Excel",
            exportar_excel(df),
            "compras.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.experimental_rerun()

# ─── Gráfico comparativo de meses ────────────────────────────────────────────────

st.subheader("📊 Comparativo de gastos entre meses")
df_res = resumo_mensal()
if df_res.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_res)
        .transform_fold(['total_gasto', 'total_itens'], as_=['Tipo', 'Valor'])
        .mark_bar()
        .encode(
            x=alt.X('mes:N', title='Mês'),
            y=alt.Y('Valor:Q', title='Valor'),
            color='Tipo:N',
            column=alt.Column('Tipo:N', title=None)
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
