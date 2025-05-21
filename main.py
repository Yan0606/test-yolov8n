import cv2
import easyocr
from ultralytics import YOLO
import re
from db_utils import criar_tabelas, inserir_dados_ficticios, verificar_placa, registrar_log
import time  # Adicione no topo do arquivo
import sys  # Adicionado para usar sys.exit()

# Função para listar câmeras disponíveis
def listar_cameras(max_test=5):
    print("Procurando câmeras conectadas...")
    cameras = []
    for i in range(max_test):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return cameras

# Seleção de câmera
cameras = listar_cameras()
if not cameras:
    print("Nenhuma câmera encontrada!")
    exit()
print("Câmeras disponíveis:")
for idx in cameras:
    print(f"{idx}: Câmera {idx}")
cam_idx = int(input("Escolha o número da câmera que deseja usar: "))
cap = cv2.VideoCapture(cam_idx)
if not cap.isOpened():
    print("Erro ao abrir a câmera selecionada!")
    exit()

# Função para carregar o modelo YOLO
def carregar_modelo():
    print("Carregando modelo de placas YOLOv8...")
    try:
        model = YOLO('license_plate_detector.pt')  # Use o nome do arquivo baixado
        print("Modelo carregado com sucesso!")
        return model
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
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
    confidence = None
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label = model.names[cls] if hasattr(model, 'names') else str(cls)
            color = (0, 255, 0) if label == 'license_plate' else (255, 0, 0)
            conf = float(box.conf[0])
            # Apenas desenha o retângulo, sem texto de label
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Se for placa, recorte para OCR
            if label == 'license_plate':
                found_plate = (x1, y1, x2, y2)
                found_plate_img = frame[y1:y2, x1:x2]
                confidence = conf
    return found_plate, found_plate_img, confidence

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

# Inicialização do banco de dados
print("Inicializando banco de dados...")
criar_tabelas()
inserir_dados_ficticios()
print("Banco de dados inicializado com sucesso!")

print("Sistema iniciado com sucesso! Pressione 'q' para sair.")

frame_count = 0
start_time = time.time()
ocr_interval = 1  # Realiza OCR a cada 2 frames para aumentar FPS
placa_autorizada = False  # Nova variável para controlar se uma placa foi autorizada

while True:
    ret, frame = cap.read()
    if not ret:
        break
    bbox, placa_img, conf = detectar_placa(frame)
    frame_count += 1

    elapsed = time.time() - start_time
    fps = frame_count / elapsed if elapsed > 0 else 0

    # Por padrão, zera as variáveis de exibição
    exibir_placa = False
    ultima_placa_texto = None
    ultima_conf = None
    ultima_status = None
    ultima_nome = None

    if bbox and placa_img is not None and frame_count % ocr_interval == 0:
        placa_texto = realizar_ocr(placa_img)
        if placa_texto:
            autorizado, nome = verificar_placa(placa_texto)
            status = 'autorizado' if autorizado else 'negado'
            registrar_log(placa_texto, status)
            ultima_placa_texto = placa_texto
            ultima_conf = conf
            ultima_status = status
            ultima_nome = nome
            exibir_placa = True
            
            # Se a placa for autorizada, marca como autorizada
            if autorizado:
                placa_autorizada = True

    # Só desenha se houver placa reconhecida neste frame
    if bbox and ultima_placa_texto and exibir_placa:
        x1, y1, x2, y2 = bbox
        cor = (0, 255, 0) if ultima_status == 'autorizado' else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
        texto_placa = f"{ultima_placa_texto}"
        texto_conf = f"{(ultima_conf or 0)*100:.1f}%"
        cv2.putText(frame, texto_placa, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)
        cv2.putText(frame, texto_conf, (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        msg = 'ACESSO AUTORIZADO' if ultima_status == 'autorizado' else 'NAO AUTORIZADO'
        cv2.putText(frame, msg, (x1, y2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 2)
        print(f"Placa: {ultima_placa_texto} | Confiança: {(ultima_conf or 0)*100:.1f}% | Status: {msg} | Nome: {ultima_nome if ultima_nome else '-'}")

    # Mostra FPS na tela
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)

    # Se uma placa foi autorizada, mostra mensagem e encerra
    if placa_autorizada:
        # Adiciona mensagem na tela
        cv2.putText(frame, "Placa autorizada! Abrindo portao...", (10, frame.shape[0] - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Reconhecimento de Placas', frame)
        cv2.waitKey(2000)  # Espera 2 segundos para mostrar a mensagem
        print("\nPlaca autorizada! Abrindo portao...")
        break

    cv2.imshow('Reconhecimento de Placas', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows() 