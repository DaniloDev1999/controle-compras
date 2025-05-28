import pandas as pd
import io

def calcular_totais(df):
    if df.empty:
        return 0.0, 0
    df["subtotal"] = df["valor_unitario"] * df["quantidade"]
    total = df["subtotal"].sum()
    qtd_total = df["quantidade"].sum()
    return total, qtd_total

def exportar_csv(df):
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")

def exportar_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue()

def classificar_categoria(nome_produto):
    nome = nome_produto.lower()
    categorias = {
        "Higiene": ["sabonete", "creme dental", "escova", "shampoo", "absorvente"],
        "Limpeza": ["sabão", "detergente", "amaciante", "desinfetante", "alvejante"],
        "Alimento": ["arroz", "feijão", "macarrão", "carne", "leite", "biscoito"],
    }
    for categoria, palavras in categorias.items():
        if any(palavra in nome for palavra in palavras):
            return categoria
    return "Outros"
