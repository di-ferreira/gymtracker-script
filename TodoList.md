# TodoList - Automação de Processamento de GIFs de Exercícios

## Arquivos de Suporte

- [x] **`.env.example`** — Template de variáveis de ambiente
- [x] **`requirements.txt`** — Dependências do projeto

## Módulos Core (skills/)

- [x] **`skills/ai_client.py`** — Cliente IA unificado (Cloud/Local)
  - [x] Classe abstrata `BaseAIClient`
  - [x] `CloudAIClient` (OpenAI + Google Gemini)
  - [x] `LocalAIClient` (Ollama/LM Studio)
  - [x] Factory `create_ai_client()`
  - [x] Rate limiting + retry com backoff
  - [x] Prompt estruturado para análise de exercícios

- [x] **`skills/api_connector.py`** — Refatorar integração REST
  - [x] `api_login()` — Auth na API
  - [x] `api_get_muscle_groups()` — Listar grupos musculares
  - [x] `api_get_movement_groups()` — Listar grupos de movimento
  - [x] `api_upload_media()` — Upload de GIF
  - [x] `api_create_exercise()` — Criar exercício
  - [x] Rate limiting + logging

- [x] **`skills/file_manager.py`** — Mantido (ok)
  - [x] `move_to_processed()` funcional e com tratamento de colisão

- [x] **`skills/media_processor.py`** — Mantido (default max_frames=3)
  - [x] `extract_gif_frames()` funcional com composição RGBA

- [x] **`skills/__init__.py`** — Exportar funções públicas

## Orquestrador

- [x] **`main.py`** — Script principal
  - [x] Carregar .env e configurar logging
  - [x] Login na API
  - [x] Fetch + cache de grupos (muscle/movement)
  - [x] Varrer recursivamente por *.gif
  - [x] Para cada GIF: analisar IA → upload → criar exercício → mover
  - [x] Tratamento de erros por arquivo (não interromper lote)
  - [x] Relatório final (total, sucessos, falhas)

## Verificação

- [x] Testar sintaxe Python (`python -m compileall`)
- [x] Validar imports de todos os módulos
- [x] Validar AST de todos os arquivos .py
- [x] Fluxo completo coerente com a API spec (Swagger)
