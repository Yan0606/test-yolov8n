# Reconhecimento Automático de Placas Veiculares com YOLOv8 e EasyOCR

Este projeto realiza a detecção automática de placas de veículos utilizando visão computacional e inteligência artificial. Ele utiliza o modelo YOLOv8 para detectar placas em tempo real a partir de uma câmera conectada ao computador e o EasyOCR para reconhecer os caracteres das placas. Os dados das placas reconhecidas são armazenados em um banco de dados MySQL.

## Tecnologias Utilizadas

- **Python 3.12+**
- **OpenCV**: Captura de vídeo e manipulação de imagens.
- **Ultralytics YOLOv8**: Detecção de placas veiculares.
- **EasyOCR**: Reconhecimento óptico de caracteres das placas.
- **MySQL**: Armazenamento dos dados das placas e logs.
- **python-dotenv**: Gerenciamento de variáveis de ambiente.
- **mysql-connector-python**: Conexão Python-MySQL.

## Como Usar

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd test-yolov8n
```

### 2. Instale as dependências

Você pode instalar todas as dependências de uma vez usando o arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

Se preferir instalar manualmente, use:

```bash
pip install opencv-python easyocr ultralytics mysql-connector-python python-dotenv
```

### 3. Configure o banco de dados

- Crie um banco de dados MySQL.
- Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis (ajuste conforme seu ambiente):



### 4. Execute o projeto

```bash
python main.py
```

- O sistema irá procurar câmeras conectadas ao seu computador.
- Escolha o número da câmera desejada.
- O sistema irá detectar placas em tempo real, reconhecer os caracteres e armazenar os dados no banco de dados.

### 5. Encerrando

- Para sair do sistema, pressione a tecla `q` na janela de vídeo.

## Observações

- Certifique-se de que sua webcam está conectada e funcionando.
- O projeto pode baixar modelos do EasyOCR na primeira execução (necessário conexão com a internet).
- O OpenCV deve ser instalado com suporte a interface gráfica (GUI) para exibir as janelas de vídeo.

---

## requirements.txt

Crie um arquivo chamado `requirements.txt` na raiz do projeto com o seguinte conteúdo:

opencv-python
easyocr
ultralytics
mysql-connector-python
python-dotenv