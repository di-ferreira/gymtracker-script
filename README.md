# GymTracker Script

Automação para processamento inteligente de GIFs de exercícios físicos usando IA multimodal com persistência via API REST.

## Fluxo da Automação

```
GIFs → IA (Cloud/Local) → JSON estruturado → Upload mídia → API → Exercício criado
```

Para cada arquivo `.gif` encontrado, o script:

1. Envia o GIF para uma IA com visão computacional
2. Extrai dados estruturados: nome, grupo muscular, equipamentos, tipo de movimento, modo de execução, dicas de segurança e tags
3. **Verifica se equipamentos, grupo muscular e tipo de movimento já existem no catálogo** — cria automaticamente se não existirem
4. **Verifica se o exercício já foi cadastrado** (por nome) — pula duplicatas
5. Faz upload do GIF para o backend
6. Cria o exercício no catálogo via API REST com os UUIDs dos relacionamentos
7. Cria instruções passo-a-passo a partir do `modo_execucao`
8. Move o GIF para uma pasta de backup

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

### File System

```env
GIF_ROOT_PATH=./1.300 GIFs de Musculação
PROCESSED_DIR=processados
```

## Uso

```bash
python main.py
```

O script exibirá logs detalhados do progresso e um relatório final com:

- Total de arquivos encontrados
- Sucessos (processados e cadastrados)
- Pulados (já existiam no catálogo)
- Falhas (erros durante o processamento)

## Funcionalidades

### Criação automática de entidades no catálogo

O script mantém um cache local dos registros da API e cria automaticamente:

- **Equipamentos** — identificados pela IA no campo `equipamentos`
- **Grupos Musculares** — extraídos do campo `musculo_primario`
- **Grupos de Movimento** — extraídos do campo `tipo_movimento` (composto, isolamento, etc.)

A busca é **case-insensitive e ignora acentos** (ex: "quadriceps" corresponde a "Quadríceps").

### Prevenção de duplicatas

Antes de criar um exercício, o script verifica se já existe um com o mesmo `nome_exercicio` no catálogo. Se existir, o GIF é movido para a pasta de processados sem criar duplicata.

### Instruções passo-a-passo

O campo `modo_execucao` retornado pela IA é parseado em etapas numeradas e cada uma é cadastrada como instrução individual no endpoint `POST /exercises/{id}/instructions/`.

### Rate Limiting

Todas as chamadas para a IA e para a API backend são controladas por rate limiting configurável via variáveis de ambiente (`AI_RATE_LIMIT`, `API_RATE_LIMIT`).

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
    ├── api_connector.py       # Integração REST: login, CRUD equipamentos/grupos/exercícios/instruções
    ├── file_manager.py        # Gerenciamento de arquivos (move_to_processed)
    └── media_processor.py     # Processamento de mídia (extract_gif_frames)
```

## API Endpoints Utilizados

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/auth/login` | Autenticação |
| GET | `/api/v1/admin/catalog/equipment/` | Lista equipamentos |
| POST | `/api/v1/admin/catalog/equipment/` | Cria equipamento |
| GET | `/api/v1/admin/catalog/muscle-groups/` | Lista grupos musculares |
| POST | `/api/v1/admin/catalog/muscle-groups/` | Cria grupo muscular |
| GET | `/api/v1/admin/catalog/movement-groups/` | Lista grupos de movimento |
| POST | `/api/v1/admin/catalog/movement-groups/` | Cria grupo de movimento |
| GET | `/api/v1/admin/catalog/exercises/` | Lista exercícios (dedup) |
| POST | `/api/v1/admin/media/upload` | Upload de arquivo GIF |
| POST | `/api/v1/admin/catalog/exercises/` | Criação de exercício |
| POST | `/api/v1/admin/catalog/exercises/{id}/instructions/` | Cria instrução |
