import sqlite3

import pandas as pd

# Abre (ou cria) o banco de dados local
conn = sqlite3.connect("gestao_produtos.db")
 
# O cursor envia comandos SQL e recebe os resultados
cursor = conn.cursor()
 
print("Conexão estabelecida com sucesso!")

def criar_tabelas():
    # O SQLite só verifica chaves estrangeiras se você pedir, a cada conexão
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.executescript('''
    DROP TABLE IF EXISTS Vendas;
    DROP TABLE IF EXISTS Produto;
    DROP TABLE IF EXISTS Categoria;
    
    CREATE TABLE Categoria (
        id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_categoria TEXT NOT NULL
    );
    
    CREATE TABLE Produto (
        id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL NOT NULL CHECK(preco >= 0.0),
        estoque INTEGER NOT NULL CHECK(estoque >= 0),
        id_categoria INTEGER,
        FOREIGN KEY (id_categoria) REFERENCES Categoria(id_categoria)
    );
    ''')
    
    conn.commit()
    print("Tabelas 'Categoria' e 'Produto' criadas com sucesso!")

def criar_tabela_vendas():

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Vendas (
        id_venda INTEGER PRIMARY KEY AUTOINCREMENT,
        id_produto INTEGER NOT NULL,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        data_venda TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (id_produto) REFERENCES Produto(id_produto)
    );
    ''')
    conn.commit()
    print("Tabela 'Vendas' criada com sucesso!")

def inserir_registros():
    categorias_iniciais = [
        ("Eletrônicos",),
        ("Móveis",),
        ("Vestuário",),
    ]
    
    # (nome, preço, estoque, id_categoria)
    produtos_iniciais = [
        ("Smartphone", 1500.00, 10, 1),
        ("Notebook", 3500.00, 5, 1),
        ("Sofá", 800.00, 3, 2),
        ("Cadeira de Escritório", 350.00, 12, 2),
        ("Camisa Polo", 80.00, 25, 3),
        ("Calça Jeans", 120.00, 15, 3),
    ]
    
    cursor.executemany(
        "INSERT INTO Categoria (nome_categoria) VALUES (?);", categorias_iniciais
    )
    cursor.executemany(
        "INSERT INTO Produto (nome, preco, estoque, id_categoria) VALUES (?, ?, ?, ?);",
        produtos_iniciais,
    )
    
    conn.commit()
    print(f"{len(categorias_iniciais)} categorias e {len(produtos_iniciais)} produtos inseridos.")

def listar_produtos():
    cursor.execute("SELECT id_produto, nome, preco, estoque FROM Produto;")
    linhas = cursor.fetchall()
    
    print("\n--- Lista de Produtos Cadastrados ---")
    for id_p, nome, preco, estoque in linhas:
        print(f"ID: {id_p} | Produto: {nome} | Preço: R$ {preco:.2f} | Estoque: {estoque}")

def atualizar_valor_produto(preco, nome):
    # 1. Atualizar o preço de um produto
    cursor.execute(
        "UPDATE Produto SET preco = ? WHERE nome = ?;", (preco, nome)
    )
    print("Linhas atualizadas:", cursor.rowcount)
    conn.commit()

def excluir_produto(nome): 
# 2. Excluir um produto
    cursor.execute("DELETE FROM Produto WHERE nome = ?;", (nome,))
    print("Linhas excluídas:", cursor.rowcount)
    
    conn.commit()

def valor_por_categoria_sql():
    """Pergunta 1 (SQL): qual o valor investido em estoque por categoria?"""
    query_estoque_categoria = """
    SELECT
        c.nome_categoria,
        COUNT(p.id_produto) AS total_produtos,
        SUM(p.preco * p.estoque) AS valor_total_estoque
    FROM Categoria c
    JOIN Produto p ON c.id_categoria = p.id_categoria
    GROUP BY c.nome_categoria
    ORDER BY valor_total_estoque DESC;
    """
    
    cursor.execute(query_estoque_categoria)
    print("\n--- Valor Total de Estoque por Categoria ---")
    for categoria, qtd, valor in cursor.fetchall():
        print(f"Categoria: {categoria} | Variedade: {qtd} item(ns) | Valor em Estoque: R$ {valor:.2f}")

def valor_por_categoria_pandas():
    df_produtos = pd.read_sql_query("""
    SELECT p.nome, p.preco, p.estoque, c.nome_categoria
    FROM Produto p
    JOIN Categoria c ON p.id_categoria = c.id_categoria
    """, conn)
    
    print("\n--- Visão Geral do DataFrame ---")
    print(df_produtos.head())
    
    print("\n--- Resumo Estatístico ---")
    print(df_produtos.describe())

def listar_produtos_pelo_valor(valor):
    """Liste os produtos com estoque menor que valor, do menor para o maior estoque."""
    cursor.execute("SELECT nome, estoque FROM Produto WHERE estoque < ? ORDER BY estoque;", (valor,))
    print(f'Produtos com valor menor que {valor}:')
    print(cursor.fetchall())

def registrar_venda(conn, id_produto, quantidade):
    """Baixa o estoque e registra a venda na mesma transação."""
    with conn:  # commit se der certo, rollback se der erro
        conn.execute(
            "UPDATE Produto SET estoque = estoque - ? WHERE id_produto = ?;",
            (quantidade, id_produto),
        )
        conn.execute(
            "INSERT INTO Vendas (id_produto, quantidade) VALUES (?, ?);",
            (id_produto, quantidade),
        )

def realizar_novas_vendas():
    """Fase 2 incluindo a tabela de vendas e realizando vendas"""

    novas_vendas = [(1, 3), (2, 2), (1, 4), (3, 1), (4, 5), (5, 10)]

    for id_produto, quantidade in novas_vendas:
        try:
            print(f"Venda registrada: {id_produto} x {quantidade}")
            registrar_venda(conn, id_produto, quantidade)
        except sqlite3.IntegrityError as erro:
            print(f"Venda recusada ({id_produto}, {quantidade}): {erro}")
 
    print("Processamento de vendas concluído.")

def mostrar_mais_vendido():
    query_campeao = """
    SELECT
        p.id_produto,
        p.nome AS produto,
        c.nome_categoria AS categoria,
        SUM(v.quantidade) AS total_unidades_vendidas,
        SUM(v.quantidade * p.preco) AS faturamento_total
    FROM Vendas v
    INNER JOIN Produto p ON v.id_produto = p.id_produto
    INNER JOIN Categoria c ON p.id_categoria = c.id_categoria
    GROUP BY p.id_produto, p.nome, c.nome_categoria
    ORDER BY total_unidades_vendidas DESC
    LIMIT 1;
    """
    
    cursor.execute(query_campeao)
    resultado = cursor.fetchone()
    
    if resultado:
        id_p, nome, categoria, total_qtd, faturamento = resultado
        print("\n--- PRODUTO MAIS VENDIDO ---")
        print(f"Produto: {nome} (ID: {id_p})")
        print(f"Categoria: {categoria}")
        print(f"Unidades vendidas: {total_qtd}")
        print(f"Faturamento gerado: R$ {faturamento:.2f}")

def mostrar_relatorio_vendas():
    query_ranking = """
    SELECT
        p.nome AS Produto,
        c.nome_categoria AS Categoria,
        p.preco AS Preco_Unitario,
        SUM(v.quantidade) AS Qtd_Vendida,
        SUM(v.quantidade * p.preco) AS Faturamento_Total,
        p.estoque AS Estoque_Restante
    FROM Produto p
    LEFT JOIN Vendas v ON p.id_produto = v.id_produto
    LEFT JOIN Categoria c ON p.id_categoria = c.id_categoria
    GROUP BY p.id_produto, p.nome, c.nome_categoria
    ORDER BY Qtd_Vendida DESC;
    """
    
    df_vendas = pd.read_sql_query(query_ranking, conn)
    
    # Produtos sem nenhuma venda aparecem com NULL; troque por zero
    df_vendas["Qtd_Vendida"] = df_vendas["Qtd_Vendida"].fillna(0).astype(int)
    df_vendas["Faturamento_Total"] = df_vendas["Faturamento_Total"].fillna(0.0)
    
    print("\n--- RANKING DE VENDAS POR PRODUTO ---")
    print(df_vendas.to_string(index=False))

def vender_produto(id_produto, quantidade):
    try:
        registrar_venda(conn, id_produto, quantidade)
        print(f"Venda registrada: {id_produto} x {quantidade}")
    except sqlite3.IntegrityError as erro:
        print(f"Venda recusada ({id_produto}, {quantidade}): {erro}")
    
    print("Processamento de vendas concluído.")

# criar_tabelas()
# criar_tabela_vendas()
# inserir_registros()

listar_produtos()
#atualizar_valor_produto(1600.00, "Smartphone")
#excluir_produto("Calça Jeans")
#listar_produtos()
#valor_por_categoria_sql()
#valor_por_categoria_pandas()
#listar_produtos_pelo_valor(10)
#realizar_novas_vendas()
mostrar_mais_vendido()
mostrar_relatorio_vendas()

# Teste de venda de produto sem estoque (100 notebooks)
vender_produto(2, 100)
listar_produtos()

cursor.close()
conn.close()
print("Conexão encerrada com segurança.")
