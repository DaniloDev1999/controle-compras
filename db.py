import sqlite3
import pandas as pd
import shutil
from utils import classificar_categoria
from datetime import datetime

def conectar():
    return sqlite3.connect("compras.db", check_same_thread=False)

def criar_tabela():
    conn = conectar()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nome TEXT,
            marca TEXT,
            fabricante TEXT,
            categoria TEXT,
            valor_unitario REAL,
            quantidade INTEGER,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

def inserir_produto(codigo, nome, marca, fabricante, categoria, valor, quantidade, data):
    conn = conectar()
    conn.execute("""
        INSERT INTO produtos (codigo, nome, marca, fabricante, categoria, valor_unitario, quantidade, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (codigo, nome, marca, fabricante, categoria, valor, quantidade, data))
    conn.commit()
    conn.close()
    hoje = datetime.now().strftime("%Y-%m-%d")
    shutil.copyfile("compras.db", f"backup_compras_{hoje}.sqlite")

def listar_produtos():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM produtos ORDER BY id DESC", conn)
    conn.close()
    return df

def listar_meses():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT data FROM produtos ORDER BY data DESC")
    meses = [row[0] for row in cursor.fetchall()]
    conn.close()
    return meses

def listar_por_mes(mes):
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM produtos WHERE data = ?", conn, params=(mes,))
    conn.close()
    return df

def limpar_mes(mes):
    conn = conectar()
    conn.execute("DELETE FROM produtos WHERE data = ?", (mes,))
    conn.commit()
    conn.close()

def resumo_mensal():
    conn = conectar()
    df = pd.read_sql_query("""
        SELECT data AS mes,
               SUM(valor_unitario * quantidade) AS total_gasto,
               SUM(quantidade) AS total_itens
        FROM produtos
        GROUP BY data
        ORDER BY data
    """, conn)
    conn.close()
    return df

def excluir_produto(id_produto):
    conn = conectar()
    conn.execute("DELETE FROM produtos WHERE id = ?", (id_produto,))
    conn.commit()
    conn.close()

def editar_produto(id_produto, nome, marca, fabricante, categoria, valor, quantidade):
    conn = conectar()
    conn.execute("""
        UPDATE produtos
        SET nome = ?, marca = ?, fabricante = ?, categoria = ?, valor_unitario = ?, quantidade = ?
        WHERE id = ?
    """, (nome, marca, fabricante, categoria, valor, quantidade, id_produto))
    conn.commit()
    conn.close()
