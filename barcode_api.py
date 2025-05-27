import requests

def buscar_produto_por_codigo(codigo_barras):
    url = f"https://world.openfoodfacts.org/api/v0/product/{codigo_barras}.json"

    try:
        resposta = requests.get(url)
        if resposta.status_code == 200:
            dados = resposta.json()
            if dados.get("status") == 1:
                produto = dados.get("product", {})
                return {
                    "nome": produto.get("product_name", "").strip(),
                    "marca": produto.get("brands", "").strip(),
                    "fabricante": "",  # Open Food Facts normalmente não fornece
                    "categoria": produto.get("categories", "").strip()
                }
    except Exception as e:
        print(f"[ERRO API OpenFoodFacts]: {e}")

    return None
