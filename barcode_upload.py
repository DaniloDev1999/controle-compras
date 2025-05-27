import requests

def cadastrar_produto_off(barcode, nome, marca, categoria):
    url = "https://world.openfoodfacts.org/cgi/product_jqm2.pl"

    # Validação mínima antes do envio
    if not all([barcode, nome, marca, categoria]):
        return False, "❗ Todos os campos (código, nome, marca e categoria) devem estar preenchidos."

    payload = {
        "code": barcode,
        "product_name": nome,
        "brands": marca,
        "categories": categoria,
        "lc": "pt",  # Linguagem: português
        "user_id": "danilo157araujo@gmail.com",
        "password": "The000vd@2025",
        "comment": "Cadastro automático via app de controle de compras",
        "add": "1",
        "submit": "Enviar"
    }

    response = requests.post(url, data=payload)

    try:
        data = response.json()
        if data.get("status") == 1:
            return True, "✅ Produto cadastrado com sucesso na Open Food Facts!"
        else:
            return False, f"❌ Erro no cadastro: {data.get('status_verbose', 'Erro desconhecido')}"
    except Exception:
        return False, f"❌ Falha ao conectar: {response.text}"
