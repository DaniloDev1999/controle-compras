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
from barcode_web import escanear_codigo_web
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# ─── Inicialização de estado ────────────────────────────────────────────────
def init_state():
    defaults = {
        "codigo": "",
        "codigo_input": "",
        "nome": "",
        "marca": "",
        "fabricante": "",
        "categoria": "",
        "valor_unitario": 0.0,
        "quantidade": 1,
        "credito_inicial": 200.0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

# Captura código escaneado via query string, se houver
query_params = st.query_params
if "barcode" in query_params:
    st.session_state["codigo_input"] = query_params["barcode"][0]
    st.session_state["codigo"] = query_params["barcode"][0]

criar_tabela()

# ─── Cabeçalho ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# ─── Controles principais ────────────────────────────────────────────────────
col_cred, = st.columns(1)
st.session_state["credito_inicial"] = st.number_input(
    "💰 Crédito disponível",
    value=st.session_state["credito_inicial"],
    min_value=0.0,
    key="credito_inicial_input"
)

meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0
)

# ─── Funções de callback ─────────────────────────────────────────────────────
def buscar_produto():
    code = st.session_state["codigo_input"].strip() or st.session_state["codigo"].strip()
    st.session_state["codigo"] = code
    if not code:
        st.warning("Por favor, informe um código de barras para buscar.")
        return
    info = buscar_produto_por_codigo(code)
    if info:
        st.session_state.update({
            "nome": info.get("nome",""),
            "marca": info.get("marca",""),
            "fabricante": info.get("fabricante",""),
            "categoria": info.get("categoria",""),
        })
        st.success("✅ Produto preenchido com sucesso!")
    else:
        st.warning("❌ Produto não encontrado na base externa.")

def adicionar_produto():
    code = st.session_state["codigo"]
    if not code:
        st.warning("Informe um código para adicionar.")
        return
    data_hoje = date.today().strftime("%Y-%m")
    inserir_produto(
        code,
        st.session_state["nome"],
        st.session_state["marca"],
        st.session_state["fabricante"],
        st.session_state["categoria"],
        st.session_state["valor_unitario"],
        st.session_state["quantidade"],
        data_hoje
    )
    st.success("✅ Produto adicionado com sucesso!")
    limpar_formulario()

def cadastrar_openfood():
    code = st.session_state["codigo"]
    nome = st.session_state["nome"]
    if not (code and nome):
        st.warning("Código e nome são obrigatórios para cadastrar.")
        return
    sucesso, msg = cadastrar_produto_off(
        code,
        nome,
        st.session_state["marca"],
        st.session_state["categoria"]
    )
    if sucesso:
        st.success(msg)
    else:
        st.error(msg)

def limpar_formulario():
    for key in ["codigo", "codigo_input", "nome", "marca", "fabricante", "categoria"]:
        st.session_state[key] = ""
    st.session_state["valor_unitario"] = 0.0
    st.session_state["quantidade"] = 1

# ─── Layout dos botões e campos ─────────────────────────────────────────────
with st.container():
    st.text_input(
        "📦 Código de barras",
        value=st.session_state["codigo_input"],
        key="codigo_input"
    )
    c1, c2, c3, c4 = st.columns([1,1,1,1.2])
    with c1:
        st.button("🔍 Buscar Produto", on_click=buscar_produto)
    with c2:
        st.button("✅ Adicionar Produto", on_click=adicionar_produto)
    with c3:
        st.button("🌍 Cadastrar na Open Food", on_click=cadastrar_openfood)
    with c4:
        # Abre o leitor (HTML+JS) e recarrega pela URL com ?barcode=
        if st.button("📷 Ler Código de Barras"):
            escanear_codigo_web()

    # Campos de preenchimento
    st.text_input("📝 Nome do produto", value=st.session_state["nome"], key="nome")
    st.text_input("🏷️ Marca", value=st.session_state["marca"], key="marca")
    st.text_input("🏭 Fabricante", value=st.session_state["fabricante"], key="fabricante")
    st.text_input("📂 Categoria", value=st.session_state["categoria"], key="categoria")

    st.number_input(
        "💵 Valor unitário",
        min_value=0.0,
        step=0.01,
        key="valor_unitario"
    )
    st.number_input(
        "🔢 Quantidade",
        min_value=1,
        step=1,
        key="quantidade"
    )

    if st.button("🧹 Limpar formulário"):
        limpar_formulario()

# ─── Exibição, exclusão e edição dos produtos do mês ────────────────────────
if mes_escolhido and mes_escolhido != "Nenhum dado":
    df_mes = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(df_mes)
    gb.configure_selection("single", use_checkbox=True)
    grid_resp = AgGrid(
        df_mes,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300
    )

    selecionados = grid_resp["selected_rows"]
    if isinstance(selecionados, list) and selecionados:
        prod = selecionados[0]
        with st.expander("🛠️ Ações para produto selecionado"):
            # Exibe detalhes
            st.write(f"**Nome:** {prod['nome']}")
            st.write(f"**Código:** {prod['codigo']}")
            st.write(f"**Marca:** {prod['marca']}")
            st.write(f"**Fabricante:** {prod['fabricante']}")
            st.write(f"**Categoria:** {prod['categoria']}")
            st.write(f"**Valor Unitário:** R$ {prod['valor_unitario']:.2f}")
            st.write(f"**Quantidade:** {prod['quantidade']}")

            # Botão excluir
            if st.button("❌ Excluir", key=f"del_{prod['id']}"):
                excluir_produto(prod["id"])
                st.success("Produto excluído.")
                st.experimental_rerun()

            # Form de edição
            with st.form(f"form_edit_{prod['id']}"):
                st.text_input("✏️ Novo nome", value=prod["nome"], key=f"edit_nome_{prod['id']}")
                st.text_input("✏️ Nova marca", value=prod["marca"], key=f"edit_marca_{prod['id']}")
                st.text_input("✏️ Novo fabricante", value=prod["fabricante"], key=f"edit_fabricante_{prod['id']}")
                st.text_input("✏️ Nova categoria", value=prod["categoria"], key=f"edit_categoria_{prod['id']}")
                st.number_input(
                    "✏️ Novo valor unitário",
                    min_value=0.0,
                    step=0.01,
                    value=float(prod["valor_unitario"]),
                    key=f"edit_valor_{prod['id']}"
                )
                st.number_input(
                    "✏️ Nova quantidade",
                    min_value=1,
                    step=1,
                    value=int(prod["quantidade"]),
                    key=f"edit_qtde_{prod['id']}"
                )
                if st.form_submit_button("💾 Salvar alteração"):
                    editar_produto(
                        prod["id"],
                        st.session_state[f"edit_nome_{prod['id']}"],
                        st.session_state[f"edit_marca_{prod['id']}"],
                        st.session_state[f"edit_fabricante_{prod['id']}"],
                        st.session_state[f"edit_categoria_{prod['id']}"],
                        st.session_state[f"edit_valor_{prod['id']}"],
                        st.session_state[f"edit_qtde_{prod['id']}"],
                    )
                    st.success("Produto atualizado.")
                    st.experimental_rerun()

# ─── Totais e exportação ─────────────────────────────────────────────────────
df_resumo = resumo_mensal()
st.subheader("📊 Comparativo de gastos entre meses")

if df_resumo.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_resumo)
        .transform_fold(['total_gasto', 'total_itens'], as_=['Tipo', 'Valor'])
        .mark_bar()
        .encode(
            x='mes:N',
            y='Valor:Q',
            color='Tipo:N',
            column='Tipo:N'
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

# Totais do mês selecionado
if mes_escolhido and mes_escolhido != "Nenhum dado":
    total, qtd = calcular_totais(listar_por_mes(mes_escolhido))
    restante = st.session_state["credito_inicial"] - total
    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Itens no mês:** {qtd}")
    st.markdown(f"**Crédito Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Crédito ultrapassado!")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📤 Exportar CSV", exportar_csv(listar_por_mes(mes_escolhido)), "compras.csv", "text/csv")
    with c2:
        st.download_button("📥 Exportar Excel", exportar_excel(listar_por_mes(mes_escolhido)), "compras.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
