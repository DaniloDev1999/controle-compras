import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_meses, listar_por_mes,
    limpar_mes, resumo_mensal, excluir_produto, editar_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

# ─── Configurações iniciais ───────────────────────────────────────────────────────

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# 1) Captura eventual barcode via URL (definido pelo leitor JS) antes de criar widgets
params = st.query_params
if "barcode" in params:
    st.session_state["codigo"] = params["barcode"][0]

# Garante que a tabela exista
criar_tabela()

# 2) Crédito disponível (guarda em session_state)
st.session_state.setdefault("credito_inicial", 200.0)
credito = st.number_input(
    "💰 Crédito disponível",
    min_value=0.0,
    value=st.session_state["credito_inicial"],
    key="credito_inicial"
)

# 3) Seleção de mês
meses = listar_meses()
mes_atual = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"],
    index=0,
    key="mes_escolhido"
)

# 4) Inicializa chaves no session_state (se ainda não existirem)
for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
    st.session_state.setdefault(campo, "")

# ─── Formulário de busca / inserção ────────────────────────────────────────────────

with st.form("formulario"):

    # Campo de código de barras, vinculado diretamente a st.session_state["codigo"]
    codigo = st.text_input("📦 Código de barras", key="codigo")

    # Botões do formulário
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
    with c1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with c2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with c3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    with c4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # Se clicou em Ler Código de Barras, dispara o componente JS
    if abrir_camera:
        escanear_codigo_web()

    # Se clicou em Buscar Produto, usa o código já na session_state
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
            st.warning("❗ Por favor, informe um código de barras para buscar.")

    # Campos manuais (já populados pelo session_state)
    nome       = st.text_input("📝 Nome do produto", key="nome")
    marca      = st.text_input("🏷️ Marca", key="marca")
    fabricante = st.text_input("🏭 Fabricante", key="fabricante")
    categoria  = st.text_input("📂 Categoria", key="categoria")
    valor_unit = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01, key="valor_unitario")
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1, key="quantidade")

    # Se clicou em Adicionar Produto
    if adicionar:
        code = st.session_state["codigo"].strip()
        if not code:
            st.warning("❗ Por favor, informe um código de barras antes de adicionar.")
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
            # Limpa todos os campos
            for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
                st.session_state[campo] = ""
            st.experimental_rerun()

    # Se clicou em Cadastrar na Open Food
    if cadastrar:
        code = st.session_state["codigo"].strip()
        nome_ = st.session_state["nome"].strip()
        if code and nome_:
            ok, msg = cadastrar_produto_off(
                code, nome_, st.session_state["marca"], st.session_state["categoria"]
            )
            st.success(msg) if ok else st.error(msg)
        else:
            st.warning("❗Para cadastrar, preencha ao menos código e nome.")

    # Botão Limpar Formulário
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria", "valor_unitario", "quantidade"]:
            st.session_state[campo] = ""
        st.experimental_rerun()

# ─── Exibição e edição dos produtos do mês ────────────────────────────────────────

if mes_atual and mes_atual != "Nenhum dado":
    df = listar_por_mes(mes_atual)
    st.subheader(f"🧾 Produtos de {mes_atual}")

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
                novo_nome       = st.text_input("✏️ Nome", value=prod["nome"], key="edit_nome")
                nova_marca      = st.text_input("🏷️ Marca", value=prod["marca"], key="edit_marca")
                novo_fabric     = st.text_input("🏭 Fabricante", value=prod["fabricante"], key="edit_fabricante")
                nova_categoria  = st.text_input("📂 Categoria", value=prod["categoria"], key="edit_categoria")
                novo_valor      = st.number_input(
                    "💵 Valor unitário",
                    min_value=0.0,
                    step=0.01,
                    value=float(prod["valor_unitario"]),
                    key="edit_valor"
                )
                nova_qtd        = st.number_input(
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
            "📥 Exportar Excel", exportar_excel(df),
            "compras.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_atual)
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
