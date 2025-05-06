import cv2
import easyocr
from ultralytics import YOLO
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
import os
from dotenv import load_dotenv
import re

# Carregar variáveis de ambiente
load_dotenv()
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'controle_portao')

# Função para conectar ao banco de dados
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

# Função para criar banco e tabelas
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

# Função para inserir dados fictícios
def inserir_dados_ficticios():
    conn = conectar_banco()
    conn.database = DB_NAME
    cursor = conn.cursor()
    dados = [
        ('ABC1234', 'Visitante A'),
        ('XYZ9876', 'Morador B'),
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

# Função para carregar o modelo YOLO
def carregar_modelo():
    print("Baixando modelo YOLOv8n.pt (isso pode demorar alguns minutos na primeira vez)...")
    try:
        model = YOLO('yolov8n.pt')
        print("Modelo carregado com sucesso!")
        return model
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        print("Tentando baixar o modelo manualmente...")
        try:
            from ultralytics.utils.downloads import download
            download('yolov8n.pt')
            model = YOLO('yolov8n.pt')
            print("Modelo baixado e carregado com sucesso!")
            return model
        except Exception as e:
            print(f"Erro ao baixar o modelo: {e}")
            return None

# Função para detectar placa usando YOLOv8
model = carregar_modelo()
if model is None:
    print("Não foi possível carregar o modelo. Encerrando o programa.")
    exit()

def detectar_placa(frame):
    results = model(frame)
    found_plate = None
    found_plate_img = None
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = model.names[cls] if hasattr(model, 'names') else str(cls)
            color = (0, 255, 0) if label == 'license_plate' else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            # Se for placa, recorte para OCR
            if label == 'license_plate':
                found_plate = (x1, y1, x2, y2)
                found_plate_img = frame[y1:y2, x1:x2]
    return found_plate, found_plate_img

# Função para realizar OCR e tratar texto
print("Inicializando EasyOCR (isso pode demorar alguns segundos)...")
ocr_reader = easyocr.Reader(['pt', 'en'], gpu=False)
print("EasyOCR inicializado com sucesso!")

# Regex para placas brasileiras (ABC1234 ou ABC1D23)
PLACA_REGEX = r'[A-Z]{3}[0-9][A-Z0-9][0-9]{2}'

def realizar_ocr(placa_img):
    if placa_img is None or placa_img.size == 0:
        return None
    resultado = ocr_reader.readtext(placa_img, detail=0, paragraph=False)
    if not resultado:
        return None
    texto = ''.join(resultado).upper()
    texto = re.sub(r'[^A-Z0-9]', '', texto)  # Remove caracteres inválidos
    match = re.search(PLACA_REGEX, texto)
    if match:
        return match.group(0)
    return texto if len(texto) >= 7 else None

# Função para verificar placa no banco
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

# Função para registrar log de acesso
def registrar_log(placa, status):
    conn = conectar_banco()
    conn.database = DB_NAME
    cursor = conn.cursor()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO logs_acesso (placa_detectada, status, data_hora) VALUES (%s, %s, %s)", (placa, status, agora))
    conn.commit()
    cursor.close()
    conn.close()

# Inicialização do banco de dados
print("Inicializando banco de dados...")
criar_tabelas()
inserir_dados_ficticios()
print("Banco de dados inicializado com sucesso!")

# Captura de vídeo
print("Iniciando captura de vídeo...")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Erro ao abrir a webcam!")
    exit()

print("Sistema iniciado com sucesso! Pressione 'q' para sair.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    bbox, placa_img = detectar_placa(frame)
    placa_texto = None
    status = None
    nome = None
    if bbox and placa_img is not None:
        placa_texto = realizar_ocr(placa_img)
        if placa_texto:
            autorizado, nome = verificar_placa(placa_texto)
            status = 'autorizado' if autorizado else 'negado'
            registrar_log(placa_texto, status)
            # Desenhar bounding box
            x1, y1, x2, y2 = bbox
            cor = (0, 255, 0) if status == 'autorizado' else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
            cv2.putText(frame, placa_texto, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)
            msg = 'ACESSO AUTORIZADO' if status == 'autorizado' else 'NÃO AUTORIZADO'
            cv2.putText(frame, msg, (x1, y2+30), cv2.FONT_HERSHEY_SIMPLEX, 1, cor, 3)
            print(f"Placa: {placa_texto} | Status: {msg} | Nome: {nome if nome else '-'}")
    cv2.imshow('Reconhecimento de Placas', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows() 