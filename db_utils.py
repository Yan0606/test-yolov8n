import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'controle_portao')

def conectar_banco():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        return None

def criar_tabelas():
    conn = conectar_banco()
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.database = DB_NAME
        cursor.execute('''CREATE TABLE IF NOT EXISTS placas_autorizadas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            placa VARCHAR(10) UNIQUE,
            nome VARCHAR(50)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs_acesso (
            id INT AUTO_INCREMENT PRIMARY KEY,
            placa_detectada VARCHAR(10),
            status ENUM('autorizado', 'negado'),
            data_hora DATETIME
        )''')
    except mysql.connector.Error as err:
        print(f"Erro ao criar tabelas: {err}")
    finally:
        cursor.close()
        conn.close()

def inserir_dados_ficticios():
    conn = conectar_banco()
    conn.database = DB_NAME
    cursor = conn.cursor()
    dados = [
        ('7394EAS', 'Visitante A'),
        ('AMQ4B44', 'Morador B'),
        ('JKL4321', 'Visitante C')
    ]
    for placa, nome in dados:
        try:
            cursor.execute("INSERT IGNORE INTO placas_autorizadas (placa, nome) VALUES (%s, %s)", (placa, nome))
        except mysql.connector.Error as err:
            print(f"Erro ao inserir dados fictícios: {err}")
    conn.commit()
    cursor.close()
    conn.close()

def verificar_placa(placa):
    conn = conectar_banco()
    conn.database = DB_NAME
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM placas_autorizadas WHERE placa = %s", (placa,))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    if resultado:
        return True, resultado[0]
    return False, None

def registrar_log(placa, status):
    conn = conectar_banco()
    conn.database = DB_NAME
    cursor = conn.cursor()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO logs_acesso (placa_detectada, status, data_hora) VALUES (%s, %s, %s)", (placa, status, agora))
    conn.commit()
    cursor.close()
    conn.close() 