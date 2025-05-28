import pandas as pd

def calcular_totais(df):
    if df.empty:
        return 0.0, 0
    df["subtotal"] = df["valor_unitario"] * df["quantidade"]
    total = df["subtotal"].sum()
    qtd_total = df["quantidade"].sum()
    return total, qtd_total

def exportar_csv(df):
    df.to_csv("registro_compras.csv", index=False)

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
