import cv2
import easyocr
from ultralytics import YOLO
import re
from db_utils import criar_tabelas, inserir_dados_ficticios, verificar_placa, registrar_log

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

# Inicialização do banco de dados
print("Inicializando banco de dados...")
criar_tabelas()
inserir_dados_ficticios()
print("Banco de dados inicializado com sucesso!")

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