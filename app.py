import streamlit as st
import altair as alt
import pandas as pd
from db import (
    criar_tabela, inserir_produto, listar_por_mes,
    listar_meses, limpar_mes, resumo_mensal,
    excluir_produto, editar_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from datetime import date
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from barcode_web import escanear_codigo_web

st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

# 1) Captura e consome parâmetro de URL "barcode"
params = st.experimental_get_query_params()
if "barcode" in params:
    st.session_state["codigo"] = params["barcode"][0]
    st.experimental_set_query_params()  # limpa o parâmetro da URL

# 2) Inicializa dados
criar_tabela()
st.session_state.setdefault("credito", 200.0)
for campo in ["codigo","nome","marca","fabricante","categoria","valor_unit","quantidade"]:
    st.session_state.setdefault(campo, "")

# 3) Crédito e mês
st.session_state["credito"] = st.number_input("💰 Crédito disponível", min_value=0.0, key="credito")
meses = listar_meses()
mes_escolhido = st.selectbox("📆 Escolha o mês", meses if meses else ["Nenhum dado"])

st.markdown("---")

# 4) Leitura de código e busca
col1, col2, col3 = st.columns([3,1,1])
with col1:
    st.text_input("📦 Código de barras", key="codigo")
with col2:
    if st.button("🔍 Buscar Produto"):
        code = st.session_state["codigo"].strip()
        if not code:
            st.warning("Informe um código de barras antes de buscar.")
        else:
            info = buscar_produto_por_codigo(code)
            if info:
                st.session_state.update({
                    "nome":       info.get("nome",""),
                    "marca":      info.get("marca",""),
                    "fabricante": info.get("fabricante",""),
                    "categoria":  info.get("categoria","")
                })
                st.success("Produto preenchido com sucesso!")
            else:
                st.warning("Produto não encontrado na base externa.")
with col3:
    if st.button("📷 Ler Código de Barras"):
        escanear_codigo_web()

st.markdown("---")

# 5) Campos manuais e ações
nome       = st.text_input("📝 Nome do produto",       key="nome")
marca      = st.text_input("🏷️ Marca",                key="marca")
fabricante = st.text_input("🏭 Fabricante",            key="fabricante")
categoria  = st.text_input("📂 Categoria",            key="categoria")
valor_unit = st.number_input("💵 Valor unitário",      min_value=0.0, step=0.01, key="valor_unit")
quantidade = st.number_input("🔢 Quantidade",          min_value=1,   step=1,    key="quantidade")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✅ Adicionar Produto"):
        code = st.session_state["codigo"].strip()
        if not code:
            st.warning("Não há código para adicionar.")
        else:
            inserir_produto(
                code, nome, marca, fabricante, categoria,
                valor_unit, quantidade, date.today().strftime("%Y-%m")
            )
            st.success("Produto adicionado com sucesso!")
            for f in ["codigo","nome","marca","fabricante","categoria","valor_unit","quantidade"]:
                st.session_state[f] = ""
            st.experimental_rerun()
with col2:
    if st.button("🌍 Cadastrar na Open Food"):
        code = st.session_state["codigo"].strip()
        if not code or not nome:
            st.warning("É preciso código e nome para cadastrar.")
        else:
            ok, msg = cadastrar_produto_off(code, nome, marca, categoria)
            st.success(msg) if ok else st.error(msg)
with col3:
    if st.button("🧹 Limpar formulário"):
        for f in ["codigo","nome","marca","fabricante","categoria","valor_unit","quantidade"]:
            st.session_state[f] = ""

st.markdown("---")

# 6) Tabela de produtos do mês e ações de edição/exclusão
if mes_escolhido != "Nenhum dado":
    dados = listar_por_mes(mes_escolhido)
    st.subheader(f"🧾 Produtos de {mes_escolhido}")
    gb = GridOptionsBuilder.from_dataframe(dados)
    gb.configure_selection("multiple", use_checkbox=True)
    grid = AgGrid(
        dados, gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        height=300
    )
    sel = grid.get("selected_rows") or []

    with st.expander("🛠️ Ações para itens selecionados"):
        if sel and st.button("❌ Excluir Selecionados"):
            for item in sel:
                excluir_produto(item["id"])
            st.warning("Excluídos!")
            st.experimental_rerun()

        if len(sel)==1:
            p = sel[0]
            st.markdown(f"""
✅ **Selecionado:** {p['nome']}  
• Código: `{p['codigo']}`  
• Valor: R$ {p['valor_unitario']:.2f}  
• Qtde: {int(p['quantidade'])}  
""")
            if st.button("✏️ Editar Este"):
                with st.form("editar"):
                    novo_nome       = st.text_input("Nome",       value=p["nome"])
                    nova_marca      = st.text_input("Marca",      value=p["marca"])
                    novo_fabricante = st.text_input("Fabricante", value=p["fabricante"])
                    nova_categoria  = st.text_input("Categoria",  value=p["categoria"])
                    novo_valor      = st.number_input("Valor unitário", min_value=0.0, value=float(p["valor_unitario"]))
                    nova_qtd        = st.number_input("Quantidade",    min_value=1, value=int(p["quantidade"]))
                    if st.form_submit_button("💾 Salvar"):
                        editar_produto(
                            p["id"],
                            novo_nome, nova_marca, novo_fabricante,
                            nova_categoria, novo_valor, nova_qtd
                        )
                        st.success("Atualizado!")
                        st.experimental_rerun()

    total, qtd = calcular_totais(dados)
    restante = st.session_state["credito"] - total
    st.markdown(f"**Total:** R$ {total:.2f} | **Itens:** {qtd} | **Crédito Restante:** R$ {restante:.2f}")
    if restante<0: st.error("Crédito ultrapassado!")

    c1,c2,c3 = st.columns(3)
    with c1:
        csv = exportar_csv(dados)
        st.download_button("📤 Exportar CSV", data=csv, file_name="dados.csv", mime="text/csv")
    with c2:
        xlsx = exportar_excel(dados)
        st.download_button("📥 Exportar Excel", data=xlsx, file_name="dados.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        if st.button("🗑️ Limpar este mês"):
            limpar_mes(mes_escolhido)
            st.warning("Limpo!")
            st.experimental_rerun()

# 7) Gráfico comparativo
st.subheader("📊 Comparativo de meses")
df_res = resumo_mensal()
if df_res.empty:
    st.info("Ainda não há dados.")
else:
    ch = (
        alt.Chart(df_res)
        .transform_fold(['total_gasto','total_itens'], as_=['Tipo','Valor'])
        .mark_bar()
        .encode(
            x='mes:N', y='Valor:Q',
            color='Tipo:N', column='Tipo:N'
        ).properties(height=300)
    )
    st.altair_chart(ch, use_container_width=True)
