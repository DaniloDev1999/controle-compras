import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_produtos,
    listar_meses, listar_por_mes, limpar_mes, resumo_mensal, excluir_produto
)
from utils import calcular_totais, exportar_csv,exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

criar_tabela()

credito_inicial = st.number_input("💰 Crédito disponível", min_value=0.0, value=200.0)

meses = listar_meses()
mes_escolhido = st.selectbox("📆 Escolha o mês", options=meses if meses else ["Nenhum dado"], index=0)

for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
    if campo not in st.session_state:
        st.session_state[campo] = ""

with st.form("formulario"):
    codigo_input = st.text_input("📦 Código de barras", value=st.session_state["codigo"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        buscar = st.form_submit_button("🔍 Buscar Produto")
    with col2:
        adicionar = st.form_submit_button("✅ Adicionar Produto")
    with col3:
        cadastrar = st.form_submit_button("🌍 Cadastrar na Open Food")
    with col4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # Ler código pela câmera
    if abrir_camera:
        escanear_codigo_web()

    # Buscar produto na API externa
    if buscar and codigo_input:
        st.session_state["codigo"] = codigo_input
        info = buscar_produto_por_codigo(codigo_input)
        if info:
            if info["nome"]:
                st.session_state["nome"] = info["nome"]
            if info["marca"]:
                st.session_state["marca"] = info["marca"]
            if info["fabricante"]:
                st.session_state["fabricante"] = info["fabricante"]
            if info["categoria"]:
                st.session_state["categoria"] = info["categoria"]
            st.success("Produto preenchido com sucesso!")
        else:
            st.warning("Produto não encontrado na base externa.")
    # Campos de entrada manual (podem ser preenchidos ou editados)
    nome = st.text_input("📝 Nome do produto", value=st.session_state["nome"])
    marca = st.text_input("🏷️ Marca", value=st.session_state["marca"])
    fabricante = st.text_input("🏭 Fabricante", value=st.session_state["fabricante"])
    categoria = st.text_input("📂 Categoria", value=st.session_state["categoria"])
    valor_unitario = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1)

    # Adicionar no banco local
    if adicionar and st.session_state["codigo"]:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(
            st.session_state["codigo"],
            nome, marca, fabricante, categoria,
            valor_unitario, quantidade, data_hoje
        )
        st.success("Produto adicionado com sucesso!")
        for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[campo] = ""
        st.rerun()

    # Cadastrar na Open Food Facts
    if cadastrar and codigo_input and nome:
        sucesso, msg = cadastrar_produto_off(
            codigo_input,
            nome,
            marca,
            categoria
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
        st.rerun()

# (o restante da aplicação continua normalmente como você já tem)


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
                    st.rerun()

                with st.form("editar_produto"):
                    novo_nome = st.text_input("✏️ Nome do produto", value=produto.get("nome"))
                    nova_marca = st.text_input("🏷️ Marca", value=produto.get("marca", ""))
                    novo_fabricante = st.text_input("🏭 Fabricante", value=produto.get("fabricante", ""))
                    nova_categoria = st.text_input("📂 Categoria", value=produto.get("categoria", ""))
                    novo_valor = st.number_input("💵 Valor unitário", value=float(produto.get("valor_unitario")), min_value=0.0)
                    nova_qtd = st.number_input("🔢 Quantidade", value=int(produto.get("quantidade")), min_value=1)

                    salvar = st.form_submit_button("💾 Salvar Alterações")
                    if salvar:
                        from db import editar_produto
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

    # 👇 Aqui está fora do if, sempre visível
    col1, col2, col3 = st.columns(3)
    with col1:
        csv_bytes = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_bytes, file_name="dados_compras.csv", mime="text/csv")

    with col2:
        excel_bytes = exportar_excel(dados)
        st.download_button("📥 Exportar Excel", data=excel_bytes, file_name="dados_compras.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col3:
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
