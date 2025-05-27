import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_produtos,
    listar_meses, listar_por_mes, limpar_mes, resumo_mensal, excluir_produto
)
from utils import calcular_totais, exportar_csv
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

criar_tabela()

credito_inicial = st.number_input("💰 Crédito disponível", min_value=0.0, value=200.0)

meses = listar_meses()
mes_escolhido = st.selectbox("📆 Escolha o mês", options=meses if meses else ["Nenhum dado"], index=0)

with st.form("formulario"):
    codigo = st.text_input("📦 Código de barras")
    nome = st.text_input("📝 Nome do produto")
    valor_unitario = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1)
    enviar = st.form_submit_button("Adicionar Produto")

    if enviar and codigo:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(codigo, nome, valor_unitario, quantidade, data_hoje)
        st.success("Produto adicionado com sucesso!")

if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("single", use_checkbox=True)

    if 'id' in dados.columns:
        gb.configure_column("id", header_name="ID", hide=False)

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

    if linha_selecionada:
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

    with st.expander("🛠️ Ações para produto selecionado"):
        if isinstance(linha_selecionada, list) and len(linha_selecionada) >= 1:
            produto = linha_selecionada[0]
            produto_id = produto.get("id")

            if produto_id is None:
                st.warning("⚠️ O campo 'id' não está presente.")
            else:
                st.markdown(f"**Produto:** `{produto.get('nome')}` — Qtd: `{produto.get('quantidade')}` — R$ {produto.get('valor_unitario'):.2f}")

                if st.button("❌ Excluir Produto Selecionado"):
                    excluir_produto(produto_id)
                    st.warning("Produto excluído.")
                    st.rerun()

                with st.form("editar_produto"):
                    novo_nome = st.text_input("✏️ Nome do produto", value=produto.get("nome"))
                    nova_qtd = st.number_input("✏️ Quantidade", value=int(produto.get("quantidade")), min_value=1)
                    novo_valor = st.number_input("✏️ Valor unitário", value=float(produto.get("valor_unitario")), min_value=0.0)

                    salvar = st.form_submit_button("💾 Salvar Alterações")
                    if salvar:
                        from db import editar_produto
                        editar_produto(produto_id, novo_nome, novo_valor, nova_qtd)
                        st.success("Produto atualizado.")
                        st.rerun()
        else:
            st.info("Selecione um item na tabela acima para ativar esta ação.")

    total, quantidade_total = calcular_totais(dados)
    valor_restante = credito_inicial - total

    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Quantidade Total:** {quantidade_total}")
    st.markdown(f"**Valor Restante:** R$ {valor_restante:.2f}")

    if valor_restante < 0:
        st.error("🚨 Você ultrapassou seu crédito disponível!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Exportar CSV"):
            exportar_csv(dados)
            st.success("Arquivo exportado com sucesso!")
    with col2:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.rerun()

st.subheader("📊 Comparativo de gastos entre meses")
df_resumo = resumo_mensal()

if df_resumo.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = alt.Chart(df_resumo).transform_fold(
        ['total_gasto', 'total_itens'],
        as_=['Tipo', 'Valor']
    ).mark_bar().encode(
        x=alt.X('mes:N', title='Mês'),
        y=alt.Y('Valor:Q', title='Valor'),
        color='Tipo:N',
        column=alt.Column('Tipo:N', title=None)
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)
