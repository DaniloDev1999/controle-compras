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

# --- Configurações iniciais ---
st.set_page_config(page_title="Controle de Compras", layout="centered")

# Lê parâmetros da URL (opcional)
params = st.experimental_get_query_params()
if "barcode" in params:
    # Se vier ?barcode=XXX, já pré-preenche o campo
    st.session_state["codigo"] = params["barcode"][0]

# Garante que a tabela exista
criar_tabela()

# Inicializa chaves de session_state
defaults = {
    "codigo": "",
    "nome": "",
    "marca": "",
    "fabricante": "",
    "categoria": "",
    "credito": 200.0
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Crédito disponível ---
credito_inicial = st.number_input(
    "💰 Crédito disponível",
    min_value=0.0,
    value=st.session_state["credito"],
    key="credito"
)

# --- Seleção de mês ---
meses = listar_meses()
mes_escolhido = st.selectbox(
    "📆 Escolha o mês",
    options=meses if meses else ["Nenhum dado"]
)

# --- Formulário de produtos ---
with st.form("formulario"):
    codigo_input = st.text_input(
        "📦 Código de barras",
        value=st.session_state["codigo"]
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

    # Leitura por câmera
    if abrir_camera:
        escanear_codigo_web()

    # Busca via API externa
    if buscar and codigo_input:
        st.session_state["codigo"] = codigo_input
        info = buscar_produto_por_codigo(codigo_input)
        if info:
            if info.get("nome"):
                st.session_state["nome"] = info["nome"]
            if info.get("marca"):
                st.session_state["marca"] = info["marca"]
            if info.get("fabricante"):
                st.session_state["fabricante"] = info["fabricante"]
            if info.get("categoria"):
                st.session_state["categoria"] = info["categoria"]
            st.success("Produto preenchido com sucesso!")
        else:
            st.warning("Produto não encontrado na base externa.")

    # Campos editáveis
    nome = st.text_input("📝 Nome do produto", value=st.session_state["nome"])
    marca = st.text_input("🏷️ Marca", value=st.session_state["marca"])
    fabricante = st.text_input("🏭 Fabricante", value=st.session_state["fabricante"])
    categoria = st.text_input("📂 Categoria", value=st.session_state["categoria"])
    valor_unitario = st.number_input("💵 Valor unitário", min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade", min_value=1, step=1)

    # Ação de adicionar ao banco local
    if adicionar and st.session_state["codigo"]:
        hoje_mes = date.today().strftime("%Y-%m")
        inserir_produto(
            st.session_state["codigo"],
            nome,
            marca,
            fabricante,
            categoria,
            valor_unitario,
            quantidade,
            hoje_mes
        )
        st.success("Produto adicionado com sucesso!")
        # Limpa campos
        for field in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[field] = ""
        st.experimental_rerun()

    # Ação de cadastrar na Open Food Facts
    if cadastrar and codigo_input and nome:
        sucesso, msg = cadastrar_produto_off(
            codigo_input, nome, marca, categoria
        )
        if sucesso:
            st.success(msg)
        else:
            st.error(msg)

    # Limpar formulário manual
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for field in ["codigo", "nome", "marca", "fabricante", "categoria"]:
            st.session_state[field] = ""
        st.experimental_rerun()

# --- Exibição dos produtos do mês ---
if mes_escolhido and mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    # Tabela interativa
    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("single", use_checkbox=True)
    grid_options = gb.build()

    grid_resp = AgGrid(
        dados,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=True,
        height=300,
    )
    selecionados = grid_resp.get("selected_rows", [])
    if isinstance(selecionados, pd.DataFrame):
        selecionados = selecionados.to_dict(orient="records")
    elif not isinstance(selecionados, list):
        selecionados = []

    with st.expander("🛠️ Ações para produto selecionado"):
        if selecionados:
            p = selecionados[0]
            st.markdown(f"""
            ✅ **Produto Selecionado:**

            • **Nome:** `{p.get('nome')}`  
            • **Código:** `{p.get('codigo')}`  
            • **Valor Unitário:** R$ {float(p.get('valor_unitario')):.2f}  
            • **Quantidade:** {int(p.get('quantidade'))}  
            • **Categoria:** `{p.get('categoria')}`  
            • **Data:** `{p.get('data')}`  
            """)
            if "id" in p:
                if st.button("❌ Excluir Produto"):
                    excluir_produto(p["id"])
                    st.warning("Produto excluído.")
                    st.experimental_rerun()

                with st.form("editar_produto"):
                    novo_nome = st.text_input("✏️ Nome", value=p.get("nome"))
                    nova_marca = st.text_input("🏷️ Marca", value=p.get("marca", ""))
                    novo_fab = st.text_input("🏭 Fabricante", value=p.get("fabricante", ""))
                    nova_cat = st.text_input("📂 Categoria", value=p.get("categoria", ""))
                    novo_val = st.number_input("💵 Valor unitário", value=float(p.get("valor_unitario")), min_value=0.0)
                    nova_qtd = st.number_input("🔢 Quantidade", value=int(p.get("quantidade")), min_value=1)

                    salvar = st.form_submit_button("💾 Salvar Alterações")
                    if salvar:
                        editar_produto(
                            p["id"],
                            novo_nome, nova_marca, novo_fab, nova_cat,
                            novo_val, nova_qtd
                        )
                        st.success("Produto atualizado.")
                        st.experimental_rerun()
        else:
            st.info("Selecione um item acima para ver ações.")

    # Totais e exportação
    total, qtd_total = calcular_totais(dados)
    restante = credito_inicial - total

    st.markdown(f"**Total Gasto:** R$ {total:.2f}")
    st.markdown(f"**Quantidade Total:** {qtd_total}")
    st.markdown(f"**Valor Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Você ultrapassou seu crédito!")

    c1, c2, c3 = st.columns(3)
    with c1:
        csv_data = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv_data, file_name="dados_compras.csv", mime="text/csv")
    with c2:
        xlsx_data = exportar_excel(dados)
        st.download_button(
            "📥 Exportar Excel",
            data=xlsx_data,
            file_name="dados_compras.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("Registros apagados.")
            st.experimental_rerun()

# --- Gráfico comparativo entre meses ---
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
