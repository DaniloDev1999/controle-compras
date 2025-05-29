import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_produtos,
    listar_meses, listar_por_mes, limpar_mes, resumo_mensal, excluir_produto, editar_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

# Configura título e layout
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# 1) Captura o código de barras da URL (definido pelo leitor JS) antes de instanciar qualquer widget
params = st.query_params
if "barcode" in params:
    st.session_state["codigo"] = params["barcode"][0]

# Garante que a tabela exista
criar_tabela()

# 2) Campo para definir crédito disponível
credito_inicial = st.number_input(
    "💰 Crédito disponível",
    min_value=0.0,
    value=st.session_state.get("credito_inicial", 200.0),
    key="credito_inicial"
)

# 3) Seleção de mês
meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0,
    key="mes_escolhido"
)

# 4) Inicializa chaves no session_state, se ainda não existirem
for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
    st.session_state.setdefault(campo, "")

# 5) Formulário de inserção / busca
with st.form("formulario"):
    # Campo de código de barras vinculado ao session_state["codigo"]
    codigo_input = st.text_input(
        "📦 Código de barras",
        key="codigo"
    )

    # Botões do formulário
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with col2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with col3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    with col4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # Se disparou a câmera, abre o leitor
    if abrir_camera:
        escanear_codigo_web()

    # Se disparou o "Buscar Produto", usa o código do session_state (que foi populado pelo leitor ou manualmente)
    if buscar:
        code = st.session_state["codigo"].strip()
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

    # Campos manuais, já populados pelo session_state
    nome       = st.text_input("📝 Nome do produto", key="nome")
    marca      = st.text_input("🏷️ Marca", key="marca")
    fabricante = st.text_input("🏭 Fabricante", key="fabricante")
    categoria  = st.text_input("📂 Categoria", key="categoria")
    valor_unit = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01, key="valor_unitario")
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1, key="quantidade")

    # Se disparou "Adicionar Produto" e há código válido
    if adicionar and st.session_state["codigo"]:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(
            st.session_state["codigo"],
            st.session_state["nome"],
            st.session_state["marca"],
            st.session_state["fabricante"],
            st.session_state["categoria"],
            st.session_state["valor_unitario"],
            st.session_state["quantidade"],
            data_hoje
        )
        st.success("Produto adicionado com sucesso!")
        # Limpa todos os campos do produto
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
            st.session_state[campo] = ""
        st.experimental_rerun()

    # Se disparou "Cadastrar na Open Food"
    if cadastrar and st.session_state["codigo"] and st.session_state["nome"]:
        sucesso, msg = cadastrar_produto_off(
            st.session_state["codigo"],
            st.session_state["nome"],
            st.session_state["marca"],
            st.session_state["categoria"]
        )
        if sucesso:
            st.success(msg)
        else:
            st.error(msg)

    # Limpar formulário completo
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
            st.session_state[campo] = ""
        st.experimental_rerun()

# ────────────────────────────────────────────────────────────────────────────
# 6) Exibição dos dados do mês escolhido
if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("single", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        dados,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300,
    )

    selecionados = grid_response.get("selected_rows", []) or []
    # Seleção única
    if selecionados:
        produto = selecionados[0]
        with st.expander("🛠️ Ações para produto selecionado"):
            st.markdown(f"""
            ✅ **Produto Selecionado:**

            • **Nome:** `{produto.get("nome")}`  
            • **Código:** `{produto.get("codigo")}`  
            • **Valor Unitário:** R$ {float(produto.get("valor_unitario")):.2f}  
            • **Quantidade:** {int(produto.get("quantidade"))}  
            • **Categoria:** `{produto.get("categoria")}`  
            • **Data:** `{produto.get("data")}`  
            """)
            # Botão de excluir
            if st.button("❌ Excluir Produto Selecionado"):
                excluir_produto(produto.get("id"))
                st.warning("Produto excluído.")
                st.experimental_rerun()
            # Formulário de edição
            with st.form("editar_produto"):
                novo_nome       = st.text_input("✏️ Nome do produto", value=produto.get("nome"), key="edit_nome")
                nova_marca      = st.text_input("🏷️ Marca", value=produto.get("marca"), key="edit_marca")
                novo_fabricante = st.text_input("🏭 Fabricante", value=produto.get("fabricante"), key="edit_fabricante")
                nova_categoria  = st.text_input("📂 Categoria", value=produto.get("categoria"), key="edit_categoria")
                novo_valor      = st.number_input(
                    "💵 Valor unitário",
                    min_value=0.0,
                    step=0.01,
                    value=float(produto.get("valor_unitario")),
                    key="edit_valor"
                )
                nova_qtd        = st.number_input(
                    "🔢 Quantidade",
                    min_value=1,
                    step=1,
                    value=int(produto.get("quantidade")),
                    key="edit_qtd"
                )
                salvar = st.form_submit_button("💾 Salvar Alterações")
                if salvar:
                    editar_produto(
                        produto.get("id"),
                        novo_nome,
                        nova_marca,
                        novo_fabricante,
                        nova_categoria,
                        novo_valor,
                        nova_qtd
                    )
                    st.success("Produto atualizado.")
                    st.experimental_rerun()

    # Totais e exportação
    total, qtd_total = calcular_totais(dados)
    valor_rest = st.session_state["credito_inicial"] - total

    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Itens no mês:** {qtd_total}")
    st.markdown(f"**Crédito Restante:** R$ {valor_rest:.2f}")
    if valor_rest < 0:
        st.error("🚨 Crédito ultrapassado!")

    col1, col2, col3 = st.columns(3)
    with col1:
        csv_bytes = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_bytes, file_name="compras.csv", mime="text/csv")
    with col2:
        excel_bytes = exportar_excel(dados)
        st.download_button(
            "📥 Exportar Excel",
            data=excel_bytes,
            file_name="compras.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.experimental_rerun()

# 7) Gráfico comparativo
st.subheader("📊 Comparativo de gastos entre meses")
df_resumo = resumo_mensal()
if df_resumo.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_resumo)
        .transform_fold(
            ['total_gasto', 'total_itens'],
            as_=['Tipo', 'Valor']
        )
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
