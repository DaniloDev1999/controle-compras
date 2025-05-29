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

# 1) Captura parâmetro da URL (window.location.search) para persistir entre reruns
query_params = st.query_params
if "barcode" in query_params:
    st.session_state["codigo"] = query_params["barcode"][0]

# 2) Garante existência das chaves no session_state
for key in ["codigo", "nome", "marca", "fabricante", "categoria"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# 3) Cria tabela no banco local
criar_tabela()

# ---- Formulário principal ----
with st.form("formulario"):
    # text_input “controlado”: tudo que o usuário digitar ou o scanner inserir
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

    # 3.1) Se clicar em “Ler Código de Barras”, abre o componente JS
    if abrir_camera:
        escanear_codigo_web()

    # 3.2) Busca na API externa usando sempre o valor atual de session_state["codigo"]
    if buscar:
        code = st.session_state["codigo"].strip()
        if code:
            info = buscar_produto_por_codigo(code)
            if info:
                st.session_state["nome"]       = info.get("nome", "")
                st.session_state["marca"]      = info.get("marca", "")
                st.session_state["fabricante"] = info.get("fabricante", "")
                st.session_state["categoria"]  = info.get("categoria", "")
                st.success("✅ Produto preenchido com sucesso!")
            else:
                st.warning("❌ Produto não encontrado na base externa.")
        else:
            st.warning("⚠️ Por favor, informe um código de barras para buscar.")

    # 3.3) Campos manuais, também “controlados” por session_state
    nome       = st.text_input("📝 Nome do produto",       key="nome")
    marca      = st.text_input("🏷️ Marca",               key="marca")
    fabricante = st.text_input("🏭 Fabricante",           key="fabricante")
    categoria  = st.text_input("📂 Categoria",           key="categoria")
    valor_unit = st.number_input("💵 Valor unitário",     min_value=0.0, step=0.01)
    quantidade = st.number_input("🔢 Quantidade",         min_value=1,   step=1)

    # 3.4) Inserir no banco local
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
        st.success("✅ Produto adicionado com sucesso!")
        # Limpa apenas os campos de produto, mantendo o restante da sessão
        for k in ["codigo","nome","marca","fabricante","categoria"]:
            st.session_state[k] = ""
        st.rerun()

    # 3.5) Cadastrar na Open Food Facts
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

    # 3.6) Limpar formulário manual
    limpar = st.form_submit_button("🧹 Limpar formulário")
    if limpar:
        for k in ["codigo","nome","marca","fabricante","categoria"]:
            st.session_state[k] = ""
        st.rerun()

# ---- Fim do formulário ----

# 4) Exibição de dados por mês
credito_inicial = st.session_state.get("credito_inicial", 200.0)
credito_inicial = st.number_input("💰 Crédito disponível", min_value=0.0, value=credito_inicial, key="credito_inicial")

meses = listar_meses()
mes_escolhido = st.selectbox("📆 Escolha o mês", options=meses if meses else ["Nenhum dado"], index=0)

if mes_escolhido != "Nenhum dado":
    df_mes = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")

    gb = GridOptionsBuilder.from_dataframe(df_mes)
    gb.configure_selection("single", use_checkbox=True)  # ou "multiple" se quiser multiseleção
    grid_options = gb.build()

    grid_resp = AgGrid(
        df_mes,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        height=300,
    )
    sel = grid_resp["selected_rows"]
    if sel:
        prod = sel[0]
        st.markdown(f"""
        **Produto Selecionado**  
        • Nome: `{prod.get("nome")}`  
        • Código: `{prod.get("codigo")}`  
        • Valor unitário: R$ {float(prod.get("valor_unitario")):.2f}  
        • Quantidade: {int(prod.get("quantidade"))}  
        • Categoria: `{prod.get("categoria")}`  
        • Data: `{prod.get("data")}`
        """)
        # Edição inline
        with st.form("editar_produto"):
            novo_nome       = st.text_input("✏️ Nome",       value=prod.get("nome",""))
            nova_marca      = st.text_input("🏷️ Marca",     value=prod.get("marca",""))
            novo_fabricante = st.text_input("🏭 Fabricante", value=prod.get("fabricante",""))
            nova_categoria  = st.text_input("📂 Categoria", value=prod.get("categoria",""))
            novo_valor      = st.number_input("💵 Valor unitário", value=float(prod.get("valor_unitario") or 0.0), min_value=0.0)
            nova_qtd        = st.number_input("🔢 Quantidade", value=int(prod.get("quantidade") or 1), min_value=1)
            salvar = st.form_submit_button("💾 Salvar alterações")

            if salvar:
                editar_produto(
                    prod.get("id"),
                    novo_nome,
                    nova_marca,
                    novo_fabricante,
                    nova_categoria,
                    novo_valor,
                    nova_qtd
                )
                st.success("✅ Produto atualizado!")
                st.rerun()

        if st.button("❌ Excluir produto selecionado"):
            excluir_produto(prod.get("id"))
            st.warning("🗑️ Produto excluído.")
            st.rerun()

    # Totais e exportações
    total, qtd = calcular_totais(df_mes)
    restante = st.session_state["credito_inicial"] - total
    st.markdown(f"**Total gasto:** R$ {total:.2f} • **Itens:** {qtd} • **Restante:** R$ {restante:.2f}")
    if restante < 0:
        st.error("🚨 Você ultrapassou seu limite!")

    c1, c2, c3 = st.columns(3)
    with c1:
        csvb = exportar_csv(df_mes)
        st.download_button("📤 Exportar CSV", data=csvb, file_name="compras.csv", mime="text/csv")
    with c2:
        xlsb = exportar_excel(df_mes)
        st.download_button("📥 Exportar Excel", data=xlsb, file_name="compras.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_escolhido)
            st.warning("📆 Dados removidos.")
            st.rerun()

# 5) Gráfico comparativo
st.subheader("📊 Comparativo de gastos entre meses")
df_res = resumo_mensal()
if df_res.empty:
    st.info("Nenhum dado para mostrar ainda.")
else:
    chart = (
        alt.Chart(df_res)
           .transform_fold(['total_gasto','total_itens'], as_=['Tipo','Valor'])
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
