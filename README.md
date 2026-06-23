# GymTracker Script

Automação para processamento inteligente de GIFs de exercícios físicos usando IA multimodal com persistência via API REST.

## Fluxo da Automação

```
GIFs → IA (Cloud/Local) → JSON estruturado → Upload mídia → API → Exercício criado
```

Para cada arquivo `.gif` encontrado, o script:
1. Envia o GIF para uma IA com visão computacional (OpenAI, Google Gemini ou Ollama/LM Studio)
2. Extrai dados estruturados: nome, grupo muscular, modo de execução, dicas de segurança e tags
3. Faz upload do arquivo para o backend
4. Cria o exercício no catálogo via API REST
5. Move o arquivo para uma pasta de backup

## Requisitos

- Python 3.10+
- Pip

## Instalação

```bash
# Clonar o repositório
cd gymtracker-script

# Criar virtual environment (opcional, mas recomendado)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API e URLs
```

## Configuração

Edite o arquivo `.env` com suas credenciais:

### Provedor de IA (Cloud — OpenAI ou Google Gemini)

```env
AI_MODE=cloud
AI_PROVIDER=openai          # openai | google
OPENAI_API_KEY=sk-...       # Sua chave OpenAI
GOOGLE_API_KEY=...          # Sua chave Google (se usar google)
AI_MODEL=gpt-4o             # Opcional: gpt-4o, gpt-4o-mini, gemini-2.5-flash, etc.
AI_RATE_LIMIT=15            # Chamadas por minuto
```

### Provedor de IA (Local — Ollama ou LM Studio)

```env
AI_MODE=local
LOCAL_API_URL=http://localhost:11434/v1/chat/completions
LOCAL_MODEL=llama3.2-vision   # Modelo com suporte a visão
AI_RATE_LIMIT=15
```

No modo local, o script extrai 3 frames-chave do GIF usando Pillow e os envia como base64 para o modelo de visão.

### API Backend

```env
API_BASE_URL=http://localhost:8000
API_EMAIL=admin@gymtracker.com
API_PASSWORD=securepass123
API_RATE_LIMIT=30
```

### Fallback IDs

O script tenta fazer fuzzy match entre o texto retornado pela IA e os grupos musculares/grupos de movimento cadastrados na API. Configure UUIDs de fallback caso o match falhe:

```env
DEFAULT_MUSCLE_GROUP_ID=<uuid>
DEFAULT_MOVEMENT_GROUP_ID=<uuid>
```

### File System

```env
GIF_ROOT_PATH=./1.300 GIFs de Musculação
PROCESSED_DIR=processados
```

## Uso

```bash
python main.py
```

O script exibirá logs detalhados do progresso e um relatório final com total de arquivos, sucessos e falhas.

## Estrutura do Projeto

```
gymtracker-script/
├── .env.example              # Template de configuração
├── requirements.txt          # Dependências
├── main.py                   # Orquestrador principal
├── TodoList.md               # Checkpoint de desenvolvimento
└── skills/
    ├── __init__.py            # Exportações públicas
    ├── ai_client.py           # Cliente IA: Cloud (OpenAI/Google) + Local (Ollama/LM Studio)
    ├── api_connector.py       # Integração REST: login, upload mídia, CRUD exercícios
    ├── file_manager.py        # Gerenciamento de arquivos (move_to_processed)
    └── media_processor.py     # Processamento de mídia (extract_gif_frames)
```

## API Endpoints Utilizados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/auth/login` | Autenticação |
| POST | `/api/v1/admin/media/upload` | Upload de arquivo GIF |
| POST | `/api/v1/admin/catalog/exercises/` | Criação de exercício |
| GET | `/api/v1/admin/catalog/muscle-groups/` | Lista grupos musculares |
| GET | `/api/v1/admin/catalog/movement-groups/` | Lista grupos de movimento |
