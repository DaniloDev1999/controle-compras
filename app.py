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

# -------------------------------------------------------
# Topo do app: lidar com query_params para capturar “barcode”
# -------------------------------------------------------
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# Se o JS de escaneamento injetou “?barcode=...” na URL, colocamos em session_state
qs = st.query_params
if "barcode" in qs and qs["barcode"]:
    st.session_state["codigo"] = qs["barcode"][0]

criar_tabela()

# -------------------------------------------------------
# Inicializar session_state se as chaves não existirem
# -------------------------------------------------------
for field in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
    if field not in st.session_state:
        # valor_unitario e quantidade vão ser numéricos—inicializamos como 0 e 1
        if field == "valor_unitario":
            st.session_state[field] = 0.0
        elif field == "quantidade":
            st.session_state[field] = 1
        else:
            st.session_state[field] = ""

# -------------------------------------------------------
# Callbacks que executam ANTES do formulário ser renderizado
# -------------------------------------------------------
def _do_scan():
    # Insere o HTML/JS para abrir a câmera e escanear; o JS acabará injetando ?barcode=...
    escanear_codigo_web()

def _do_busca():
    codigo = st.session_state["codigo"]
    if not codigo:
        st.warning("▶️ Digite ou escaneie um código antes de buscar.")
        return

    info = buscar_produto_por_codigo(codigo)
    if info:
        if info["nome"]:
            st.session_state["nome"] = info["nome"]
        if info["marca"]:
            st.session_state["marca"] = info["marca"]
        if info["fabricante"]:
            st.session_state["fabricante"] = info["fabricante"]
        if info["categoria"]:
            st.session_state["categoria"] = info["categoria"]
        st.success("✅ Produto preenchido com sucesso!")
    else:
        st.warning("❌ Produto não encontrado na base externa.")

def _do_adicionar():
    codigo = st.session_state["codigo"]
    nome = st.session_state["nome"]
    marca = st.session_state["marca"]
    fabricante = st.session_state["fabricante"]
    categoria = st.session_state["categoria"]
    valor = st.session_state["valor_unitario"]
    qtd = st.session_state["quantidade"]

    if not codigo or not nome:
        st.error("📌 Para adicionar, é necessário preencher pelo menos ‘código’ e ‘nome’.")
        return

    hoje = date.today().strftime("%Y-%m")
    inserir_produto(
        codigo, nome, marca, fabricante, categoria, valor, qtd, hoje
    )
    st.success("✅ Produto adicionado com sucesso!")

    # Limpamos todos exceto “codigo”
    for fld in ["nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
        if fld == "valor_unitario":
            st.session_state[fld] = 0.0
        elif fld == "quantidade":
            st.session_state[fld] = 1
        else:
            st.session_state[fld] = ""

def _do_limpar():
    # Limpa todos exceto “codigo”
    for fld in ["nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
        if fld == "valor_unitario":
            st.session_state[fld] = 0.0
        elif fld == "quantidade":
            st.session_state[fld] = 1
        else:
            st.session_state[fld] = ""

# -------------------------------------------------------
# Formulário principal
# -------------------------------------------------------
with st.form("formulario", clear_on_submit=False):
    # “Código de barras” vinculado diretamente a st.session_state["codigo"]
    codigo_input = st.text_input("📦 Código de barras", key="codigo")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        st.form_submit_button("🔍 Buscar Produto", on_click=_do_busca)
    with col2:
        st.form_submit_button("✅ Adicionar Produto", on_click=_do_adicionar)
    with col3:
        st.form_submit_button(
            "🌍 Cadastrar na Open Food",
            on_click=lambda: cadastrar_produto_off(
                st.session_state["codigo"],
                st.session_state["nome"],
                st.session_state["marca"],
                st.session_state["categoria"]
            )
        )
    with col4:
        st.form_submit_button("📷 Ler Código de Barras", on_click=_do_scan)

    # Os demais campos vêm “grudados” ao session_state
    nome = st.text_input("📝 Nome do produto", key="nome")
    marca = st.text_input("🏷️ Marca", key="marca")
    fabricante = st.text_input("🏭 Fabricante", key="fabricante")
    categoria = st.text_input("📂 Categoria", key="categoria")
    valor_unitario = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01, key="valor_unitario")
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1, key="quantidade")

    # Botão “Limpar formulário” que apenas limpa os campos manuais
    st.form_submit_button("🧹 Limpar formulário", on_click=_do_limpar)

# -------------------------------------------------------
# Se o usuário escolheu um mês existente, mostramos a lista
# -------------------------------------------------------
meses = listar_meses()
mes_escolhido = st.selectbox("📆 Escolha o mês", options=meses if meses else ["Nenhum dado"], index=0)

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

    linha_selecionada = grid_response.get("selected_rows", [])
    if isinstance(linha_selecionada, pd.DataFrame):
        linha_selecionada = linha_selecionada.to_dict(orient="records")
    elif not isinstance(linha_selecionada, list):
        linha_selecionada = []

    with st.expander("🛠️ Ações para produto selecionado"):
        if isinstance(linha_selecionada, list) and len(linha_selecionada) >= 1:
            produto = linha_selecionada[0]
            st.markdown(f"""
            ✅ **Produto Selecionado:**

            • **Nome:** `{produto.get("nome")}`  
            • **Código:** `{produto.get("codigo")}`  
            • **Valor Unitário:** R$ {float(produto.get("valor_unitario")):.2f}  
            • **Quantidade:** {int(produto.get("quantidade"))}  
            • **Categoria:** `{produto.get("categoria")}`  
            • **Data:** `{produto.get("data")}`  
            """)

            if "id" not in produto:
                st.error("❗ O campo 'id' não está presente.")
            else:
                if st.button("❌ Excluir Produto Selecionado"):
                    excluir_produto(produto.get("id"))
                    st.warning("Produto excluído.")
                    st.experimental_rerun()

                with st.form("editar_produto"):
                    novo_nome = st.text_input("✏️ Nome do produto", value=produto.get("nome"))
                    nova_marca = st.text_input("🏷️ Marca", value=produto.get("marca", ""))
                    novo_fabricante = st.text_input("🏭 Fabricante", value=produto.get("fabricante", ""))
                    nova_categoria = st.text_input("📂 Categoria", value=produto.get("categoria", ""))
                    novo_valor = st.number_input(
                        "💵 Valor unitário",
                        value=float(produto.get("valor_unitario")),
                        min_value=0.0
                    )
                    nova_qtd = st.number_input(
                        "🔢 Quantidade",
                        value=int(produto.get("quantidade")),
                        min_value=1
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
                        st.success("✅ Produto atualizado.")
                        st.experimental_rerun()
        else:
            st.info("Selecione um item na tabela acima para ativar esta ação.")

    total, quantidade_total = calcular_totais(dados)
    valor_restante = st.session_state.get("credito_inicial", 200.0) - total

    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Quantidade Total:** {quantidade_total}")
    st.markdown(f"**Valor Restante:** R$ {valor_restante:.2f}")

    if valor_restante < 0:
        st.error("🚨 Você ultrapassou seu crédito disponível!")

    col1, col2, col3 = st.columns(3)
    with col1:
        csv_bytes = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_bytes, file_name="dados_compras.csv", mime="text/csv")

    with col2:
        excel_bytes = exportar_excel(dados)
        st.download_button(
            "📥 Exportar Excel",
            data=excel_bytes,
            file_name="dados_compras.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("🗑️ Registros apagados.")
            st.experimental_rerun()

# -------------------------------------------------------
# Gráfico de comparativo mensal
# -------------------------------------------------------
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
            x=alt.X("mes:N", title="Mês"),
            y=alt.Y("Valor:Q", title="Valor"),
            color="Tipo:N",
            column=alt.Column("Tipo:N", title=None),
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
