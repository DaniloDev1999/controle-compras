import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_produtos,
    listar_meses, listar_por_mes, limpar_mes, resumo_mensal, excluir_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# Inicializa crédito em session_state, se ainda não existe
if "credito" not in st.session_state:
    st.session_state.credito = 200.0

# Widget de crédito gerenciado via key="credito"
credito_inicial = st.number_input(
    "💰 Crédito disponível",
    min_value=0.0,
    key="credito"
)

# Captura código lido pela câmera via URL
query_params = st.query_params
if "barcode" in query_params:
    st.session_state["codigo"] = query_params["barcode"][0]

criar_tabela()

meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"]
)

# Garante chaves iniciais no session_state
for campo in ["codigo", "nome", "marca", "fabricante", "categoria"]:
    if campo not in st.session_state:
        st.session_state[campo] = ""

with st.form("formulario"):
    # a partir de agora o input fica “controlado” por st.session_state["codigo"]
    codigo_input = st.text_input(
        "📦 Código de barras",
        key="codigo"
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        buscar      = st.form_submit_button("🔍 Buscar Produto")
    with col2:
        adicionar   = st.form_submit_button("✅ Adicionar Produto")
    with col3:
        cadastrar   = st.form_submit_button("🌍 Cadastrar na Open Food")
    with col4:
        abrir_camera = st.form_submit_button("📷 Ler Código de Barras")

    # dispara o leitor; ele vai escrever diretamente em st.session_state["codigo"]
    if abrir_camera:
        escanear_codigo_web()

    # busca produto usando sempre o que estiver em st.session_state["codigo"]
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

    # campos manuais populados pelo session_state
    nome       = st.text_input("📝 Nome do produto",       key="nome")
    marca      = st.text_input("🏷️ Marca",               key="marca")
    fabricante = st.text_input("🏭 Fabricante",           key="fabricante")
    categoria  = st.text_input("📂 Categoria",           key="categoria")
    valor_unit = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade",     min_value=1,   step=1)

    # inserir no DB
    if adicionar and st.session_state["codigo"]:
        data_hoje = date.today().strftime("%Y-%m")
        inserir_produto(
            st.session_state["codigo"],
            st.session_state["nome"],
            st.session_state["marca"],
            st.session_state["fabricante"],
            st.session_state["categoria"],
            valor_unit,
            quantidade,
            data_hoje
        )
        st.success("Produto adicionado com sucesso!")
        # limpa apenas os campos do produto
        for campo in ["codigo","nome","marca","fabricante","categoria"]:
            st.session_state[campo] = ""
        st.rerun()

    # cadastrar na Open Food Facts
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

    # limpar formulário
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for campo in ["codigo","nome","marca","fabricante","categoria"]:
            st.session_state[campo] = ""
        st.rerun()

# Exibe tabela de compras do mês selecionado
if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(dados)
    # Seleção múltipla agora
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
    if isinstance(selecionados, pd.DataFrame):
        selecionados = selecionados.to_dict("records")
    elif not isinstance(selecionados, list):
        selecionados = []

    with st.expander("🛠️ Ações para produto(s) selecionado(s)"):
        # Botão para excluir em lote
        if selecionados:
            if st.button("❌ Excluir Selecionados"):
                for prod in selecionados:
                    if "id" in prod:
                        excluir_produto(prod["id"])
                st.warning("Produtos excluídos.")
                st.rerun()

        # Se exatamente 1 for selecionado, mostra formulário de edição
        if len(selecionados) == 1:
            produto = selecionados[0]
            st.markdown(f"""
✅ **Produto Selecionado:**
• **Nome:** `{produto['nome']}`  
• **Código:** `{produto['codigo']}`  
• **Valor Unitário:** R$ {produto['valor_unitario']:.2f}  
• **Quantidade:** {int(produto['quantidade'])}  
• **Categoria:** `{produto['categoria']}`  
• **Data:** `{produto['data']}`  
""")
            with st.form("editar_produto"):
                novo_nome       = st.text_input("✏️ Nome", value=produto["nome"])
                nova_marca      = st.text_input("🏷️ Marca", value=produto["marca"])
                novo_fabricante = st.text_input("🏭 Fabricante", value=produto["fabricante"])
                nova_categoria  = st.text_input("📂 Categoria", value=produto["categoria"])
                # força float(...) para evitar MixedNumericTypesError
                novo_valor      = st.number_input(
                    "💵 Valor unitário",
                    min_value=0.0,
                    value=float(produto["valor_unitario"])
                )
                nova_qtd        = st.number_input(
                    "🔢 Quantidade",
                    min_value=1,
                    value=int(produto["quantidade"])
                )
                salvar = st.form_submit_button("💾 Salvar Alterações")
                if salvar:
                    from db import editar_produto
                    editar_produto(
                        produto["id"],
                        novo_nome,
                        nova_marca,
                        novo_fabricante,
                        nova_categoria,
                        novo_valor,
                        nova_qtd
                    )
                    st.success("Produto atualizado.")
                    st.rerun()
        elif selecionados:
            st.info("Para editar, selecione apenas um produto de cada vez.")

    # Totais e crédito restante
    total, qtd_total = calcular_totais(dados)
    restante = st.session_state.credito - total
    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Itens Totais:** {qtd_total}")
    st.markdown(f"**Crédito Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Você ultrapassou o crédito disponível!")

    # Exportar e limpar mês
    col1, col2, col3 = st.columns(3)
    with col1:
        csv_bytes = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_bytes,
                           file_name="dados_compras.csv", mime="text/csv")
    with col2:
        excel_bytes = exportar_excel(dados)
        st.download_button("📥 Exportar Excel", data=excel_bytes,
                           file_name="dados_compras.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col3:
        if st.button("🗑️ Limpar este mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.rerun()

# Gráfico comparativo
st.subheader("📊 Comparativo de gastos entre meses")
df_resumo = resumo_mensal()
if df_resumo.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_resumo)
        .transform_fold(['total_gasto', 'total_itens'], as_=['Tipo','Valor'])
        .mark_bar()
        .encode(
            x=alt.X('mes:N', title='Mês'),
            y=alt.Y('Valor:Q', title='Valor'),
            color='Tipo:N',
            column=alt.Column('Tipo:N', title=None),
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)
