# ms_estoque/database.py
import sqlite3

def inicializar_banco():
    conn = sqlite3.connect('estoque.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    
    # popula o banco apenas na primeira inicializacao
    cursor.execute('SELECT COUNT(*) FROM produtos')
    if cursor.fetchone()[0] == 0:
        dados_iniciais = [
            (1, 'Caderno', 15.50, 10),
            (2, 'Caneta', 2.50, 20),
            (3, 'Mochila', 120.00, 5)
        ]
        cursor.executemany(
            'INSERT INTO produtos (id, nome, preco, quantidade) VALUES (?, ?, ?, ?)',
            dados_iniciais
        )
    
    conn.commit()
    conn.close()

def buscar_produtos():
    conn = sqlite3.connect('estoque.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, preco, quantidade FROM produtos')
    linhas = cursor.fetchall()
    conn.close()
    
    lista_final = []

    for r in linhas: 
        produto_formatado = {
            "id_produto": r[0], 
            "nome": r[1], 
            "preco": r[2], 
            "quantidade": r[3]
        }
        lista_final.append(produto_formatado)

    return lista_final