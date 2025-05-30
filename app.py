import streamlit as st
import altair as alt
import pandas as pd
from datetime import date
from db import (
    criar_tabela, inserir_produto, listar_meses, listar_por_mes,
    limpar_mes, resumo_mensal, excluir_produto, editar_produto
)
from utils import calcular_totais, exportar_csv, exportar_excel
from barcode_api import buscar_produto_por_codigo
from barcode_upload import cadastrar_produto_off
from barcode_web import escanear_codigo_web
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# ─── Inicializa session_state ──────────────────────────────────────────────────
defaults = {
    "form_codigo": "",
    "form_nome": "",
    "form_marca": "",
    "form_fabricante": "",
    "form_categoria": "",
    "form_valor": 0.0,
    "form_qtd": 1
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─── Callbacks ─────────────────────────────────────────────────────────────────
def abrir_leitor():
    escanear_codigo_web()

def buscar_callback():
    code = st.session_state["form_codigo"].strip()
    if not code:
        st.warning("❗ Informe um código de barras para buscar.")
        return
    info = buscar_produto_por_codigo(code)
    if not info:
        st.warning("❌ Produto não encontrado.")
        return
    st.session_state["form_nome"]       = info.get("nome", "")
    st.session_state["form_marca"]      = info.get("marca", "")
    st.session_state["form_fabricante"] = info.get("fabricante", "")
    st.session_state["form_categoria"]  = info.get("categoria", "")
    st.success("✅ Produto preenchido com sucesso!")

def adicionar_callback():
    codigo = st.session_state["form_codigo"].strip()
    if not codigo:
        st.warning("❗ Não há código de barras para adicionar.")
        return
    inserir_produto(
        codigo,
        st.session_state["form_nome"],
        st.session_state["form_marca"],
        st.session_state["form_fabricante"],
        st.session_state["form_categoria"],
        st.session_state["form_valor"],
        st.session_state["form_qtd"],
        date.today().strftime("%Y-%m")
    )
    st.success("✅ Produto adicionado com sucesso!")
    limpar_callback()

def cadastrar_callback():
    codigo = st.session_state["form_codigo"].strip()
    nome   = st.session_state["form_nome"].strip()
    if not codigo or not nome:
        st.warning("❗ Código e nome obrigatórios para cadastrar.")
        return
    sucesso, msg = cadastrar_produto_off(
        codigo,
        nome,
        st.session_state["form_marca"],
        st.session_state["form_categoria"]
    )
    if sucesso:
        st.success(msg)
    else:
        st.error(msg)

def limpar_callback():
    for key in defaults:
        st.session_state[key] = defaults[key]

# ─── App ───────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Controle de Compras", layout="centered")
st.title("🛒 Controle de Compras por Código de Barras")

criar_tabela()

# Botão de câmera
st.button("📷 Ler Código de Barras", on_click=abrir_leitor)

# Quando o JS coloca ?barcode=…, atualiza session_state
params = st.experimental_get_query_params()  # ou st.query_params
if "barcode" in params:
    st.session_state["form_codigo"] = params["barcode"][0]

# Campos do formulário
st.text_input("📦 Código de barras", key="form_codigo")
st.text_input("📝 Nome do produto", key="form_nome")
st.text_input("🏷️ Marca", key="form_marca")
st.text_input("🏭 Fabricante", key="form_fabricante")
st.text_input("📂 Categoria", key="form_categoria")
st.number_input("💵 Valor unitário", min_value=0.0, step=0.01, key="form_valor")
st.number_input("🔢 Quantidade", min_value=1, step=1, key="form_qtd")

# Botões de ação
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.button("🔍 Buscar Produto", on_click=buscar_callback)
with col2:
    st.button("✅ Adicionar Produto", on_click=adicionar_callback)
with col3:
    st.button("🌍 Cadastrar na Open Food", on_click=cadastrar_callback)
with col4:
    st.button("🧹 Limpar Formulário", on_click=limpar_callback)

st.markdown("---")

# Seleção de mês
mes_atual = st.selectbox(
    "📆 Escolha o mês",
    options=list(listar_meses()) or ["Nenhum dado"],
    index=0
)

# Exibe tabela interativa
df = listar_por_mes(mes_atual) if mes_atual and mes_atual != "Nenhum dado" else pd.DataFrame()
if df.empty:
    st.info("🛈 Sem registros para este mês.")
else:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection("single", use_checkbox=True)
    grid_resp = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        height=300
    )
    sel = grid_resp["selected_rows"]
    if sel:
        prod = sel[0]
        with st.expander("🛠️ Ações para produto selecionado"):
            st.write(f"**Nome:** {prod['nome']}")
            st.write(f"**Código:** {prod['codigo']}")
            st.write(f"**Marca:** {prod['marca']}")
            st.write(f"**Fabricante:** {prod['fabricante']}")
            st.write(f"**Categoria:** {prod['categoria']}")
            st.write(f"**Valor unitário:** R$ {prod['valor_unitario']:.2f}")
            st.write(f"**Quantidade:** {prod['quantidade']}")
            if st.button("❌ Excluir Produto"):
                excluir_produto(prod["id"])
                st.warning("🗑️ Produto excluído.")
                st.experimental_rerun()
            # Form de edição
            with st.form("edit_form"):
                prefix = f"edit_{prod['id']}_"
                new_nome  = st.text_input("✏️ Nome", value=prod["nome"], key=prefix+"nome")
                new_marca = st.text_input("🏷 Marca", value=prod["marca"], key=prefix+"marca")
                new_fab   = st.text_input("🏭 Fabricante", value=prod["fabricante"], key=prefix+"fab")
                new_cat   = st.text_input("📂 Categoria", value=prod["categoria"], key=prefix+"cat")
                new_val   = st.number_input(
                    "💵 Valor unitário",
                    min_value=0.0,
                    step=0.01,
                    value=float(prod["valor_unitario"]),
                    key=prefix+"val"
                )
                new_qtd   = st.number_input(
                    "🔢 Quantidade",
                    min_value=1,
                    step=1,
                    value=int(prod["quantidade"]),
                    key=prefix+"qtd"
                )
                if st.form_submit_button("💾 Salvar Alterações"):
                    editar_produto(
                        prod["id"],
                        new_nome, new_marca, new_fab,
                        new_cat, new_val, new_qtd
                    )
                    st.success("✅ Produto atualizado.")
                    st.experimental_rerun()

    # Totais e exportação
    total, qtd = calcular_totais(df)
    rest = st.session_state.get("credito_inicial", 0.0) - total
    st.markdown(f"**Total Gasto:** R$ {total:.2f} — **Itens:** {qtd} — **Restante:** R$ {rest:.2f}")
    if rest < 0:
        st.error("🚨 Crédito ultrapassado!")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📤 Exportar CSV", exportar_csv(df), "compras.csv", "text/csv")
    with c2:
        st.download_button(
            "📥 Exportar Excel",
            exportar_excel(df),
            "compras.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c3:
        if st.button("🗑️ Limpar dados deste mês"):
            limpar_mes(mes_atual)
            st.warning("🗑️ Dados apagados.")
            st.experimental_rerun()

st.markdown("---")
# Gráfico comparativo
st.subheader("📊 Comparativo de gastos entre meses")
df_res = resumo_mensal()
if df_res.empty:
    st.info("🛈 Sem dados para gráfico.")
else:
    chart = (
        alt.Chart(df_res)
        .transform_fold(['total_gasto','total_itens'], as_=['Tipo','Valor'])
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
