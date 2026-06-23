# TodoList - Automação de Processamento de GIFs de Exercícios

## Arquivos de Suporte

- [x] **`.env.example`** — Template de variáveis de ambiente (removido DEFAULT_*_ID)
- [x] **`requirements.txt`** — Dependências do projeto

## Módulos Core (skills/)

- [x] **`skills/ai_client.py`** — Cliente IA unificado (Cloud/Local)
  - [x] Classe abstrata `BaseAIClient`
  - [x] `CloudAIClient` (OpenAI + Google Gemini)
  - [x] `LocalAIClient` (Ollama/LM Studio)
  - [x] Factory `create_ai_client()`
  - [x] Rate limiting + retry com backoff
  - [x] Prompt estruturado para análise de exercícios
  - [x] **Prompt atualizado** — Campos `equipamentos`, `musculo_primario`, `tipo_movimento`

- [x] **`skills/api_connector.py`** — Integração REST completa
  - [x] `api_login()` — Auth na API
  - [x] `api_get_equipment()` / `api_create_equipment()` — CRUD equipamentos
  - [x] `api_get_muscle_groups()` / `api_create_muscle_group()` — CRUD grupos musculares
  - [x] `api_get_movement_groups()` / `api_create_movement_group()` — CRUD grupos de movimento
  - [x] `api_get_exercises()` — Listar exercícios (para dedup)
  - [x] `api_upload_media()` — Upload de GIF (fallback para url/file_url/path)
  - [x] `api_create_exercise()` — Criar exercício
  - [x] `api_create_instruction()` — Criar instrução passo-a-passo
  - [x] Rate limiting + logging

- [x] **`skills/file_manager.py`** — Mantido (ok)
  - [x] `move_to_processed()` funcional e com tratamento de colisão

- [x] **`skills/media_processor.py`** — Mantido (default max_frames=3)
  - [x] `extract_gif_frames()` funcional com composição RGBA

- [x] **`skills/__init__.py`** — Exportar todas as funções públicas

## Orquestrador

- [x] **`main.py`** — Script principal refatorado
  - [x] Login + cache completo (equipamentos, grupos musculares, movimentos, exercícios)
  - [x] Para cada GIF:
    1. IA analisa → JSON com equipamentos, músculo primário, tipo de movimento
    2. **Equipamentos**: verifica se existe → cria se não existir
    3. **Grupo muscular**: extrai `musculo_primario` → cria se não existir
    4. **Grupo de movimento**: extrai `tipo_movimento` → cria se não existir
    5. **Dedup**: verifica se exercício já existe pelo nome → pula se sim
    6. Upload mídia → cria exercício → cria instruções (steps) → move
  - [x] Normalização Unicode para matching case-insensitive sem acentos
  - [x] Tratamento de erros por arquivo (não interrompe lote)
  - [x] Relatório final (total, sucessos, pulados, falhas)

## Verificação

- [x] Testar sintaxe Python (`python -m compileall`)
- [x] Validar imports de todos os módulos
- [x] Testes funcionais: `_find_by_name` com/sem acentos, `_parse_instructions_to_steps`
