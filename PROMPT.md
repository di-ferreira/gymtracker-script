# Prompt Engineering — Análise de Exercícios com IA Multimodal

## Arquitetura do Prompt

O prompt é dividido em duas camadas enviadas à IA:

```
[System Prompt] → Define o papel, regras e schema JSON esperado
[User Message]  → Nome do arquivo + mídia (GIF ou frames)
```

### System Prompt (diretrizes fixas)

Define o papel do modelo como **especialista em biomecânica e cinesiologia**, impõe o **schema JSON obrigatório** e lista **valores controlados** para campos como `tags`, `musculo_primario` e `equipamentos`.

### User Message (contexto variável por exercício)

```
"Analise o exercício no arquivo: {file_name}"
+ mídia (GIF completo para cloud, 3 frames JPEG para local)
```

---

## Schema JSON de Saída

```json
{
  "nome_exercicio": "string — Nome padronizado e comercial do exercício em português",
  "grupo_muscular": "string — Descrição textual dos músculos principais e secundários ativados",
  "musculo_primario": "string — Grupo muscular principal (valores controlados)",
  "modo_execucao": "string — Passo a passo numerado (1. ..., 2. ..., etc.)",
  "dicas_seguranca": "string — Alertas de postura e erros comuns",
  "equipamentos": ["string"] — Lista de equipamentos utilizados",
  "tipo_movimento": "string — composto | isolamento | funcional | calistenia",
  "dificuldade": "string — iniciante | intermediario | avancado | expert",
  "exercicios_alternativos": ["string"] — Lista de nomes de exercícios similares ou alternativos",
  "tags": ["string"] — Palavras-chave para busca"
}
```

### Regras de validação por campo

| Campo | Obrigatório | Valores permitidos / Formato |
|-------|-------------|------------------------------|
| `nome_exercicio` | Sim | Texto livre. Deve ser o nome comercial padronizado |
| `grupo_muscular` | Sim | Texto descritivo livre |
| `musculo_primario` | Sim | `Quadríceps`, `Peitoral`, `Costas`, `Glúteos`, `Ombros`, `Bíceps`, `Tríceps`, `Abdômen`, `Panturrilha`, `Trapézio`, `Antebraço`, `Posterior de Coxa` |
| `modo_execucao` | Sim | Deve conter etapas numeradas (1. 2. 3.) |
| `dicas_seguranca` | Sim | Texto livre com alertas |
| `equipamentos` | Sim | Array. Valores comuns: `halteres`, `barra`, `banco`, `máquina`, `cabo`, `elástico`, `smith`, `bola`, `step`, `kettlebell`, `peso corporal` |
| `tipo_movimento` | Sim | `composto`, `isolamento`, `funcional`, `calistenia` |
| `dificuldade` | Não | `iniciante`, `intermediario`, `avancado`, `expert`. Default: `intermediario` |
| `exercicios_alternativos` | Não | Array de nomes de exercícios similares. Opcional. |
| `tags` | Sim | Mínimo 3 tags. Use os valores sugeridos no prompt |

---

## Estratégias de Prompt por Provedor

### OpenAI (GPT-4o / GPT-4o-mini)

```python
response_format={"type": "json_object"}
```

- O parâmetro `response_format` com `json_object` garante que a resposta seja JSON válido.
- O modelo recebe o GIF completo como base64 (`data:image/gif;base64,...`).
- Suporta análise direta de GIFs animados.

### Google Gemini (Gemini 2.5 Flash / Pro)

```python
config=types.GenerateContentConfig(response_mime_type="application/json")
```

- `response_mime_type="application/json"` força saída JSON estruturada.
- O GIF é enviado via `client.files.upload()` que retorna um `file_ref`.
- Gemini processa GIFs animados nativamente.

### Local (Ollama / LM Studio)

- Modelos de visão locais (llama3.2-vision, llava) **não processam GIFs** diretamente.
- **Estratégia**: extrair 3 frames estáticos do GIF com `extract_gif_frames()` e enviar como JPEG base64.
- A saída JSON é validada e, se inválida, o prompt original é reenviado com instrução explícita "Retorne APENAS JSON válido, sem markdown".

---

## Few-Shot Examples

Quando o modelo local retorna JSON inválido ou campos inconsistentes, inclua um example no user message:

### Exemplo 1: Agachamento Livre

```json
{
  "nome_exercicio": "Agachamento Livre",
  "grupo_muscular": "Quadríceps (principal), Glúteos Máximos, Posterior de Coxa, Eretores da Espinha (secundários)",
  "musculo_primario": "Quadríceps",
  "modo_execucao": "1. Posicione a barra sobre os ombros, atrás do pescoço. 2. Mantenha os pés na largura dos ombros. 3. Desça flexionando joelhos e quadris até as coxas ficarem paralelas ao chão. 4. Expire e suba voltando à posição inicial.",
  "dicas_seguranca": "Mantenha a coluna neutra durante todo o movimento. Não deixe os joelhos ultrapassarem a ponta dos pés. Evite curvar as costas.",
  "equipamentos": ["barra", "anilhas"],
  "tipo_movimento": "composto",
  "tags": ["pernas", "quadriceps", "gluteos", "agachamento", "barra", "basico"]
}
```

### Exemplo 2: Rosca Direta com Halteres

```json
{
  "nome_exercicio": "Rosca Direta com Halteres",
  "grupo_muscular": "Bíceps Braquial (principal), Braquial, Braquiorradial (secundários)",
  "musculo_primario": "Bíceps",
  "modo_execucao": "1. Em pé, segure um halter em cada mão com as palmas voltadas para frente. 2. Mantenha os cotovelos fixos ao lado do corpo. 3. Flexione os cotovelos elevando os halteres em direção aos ombros. 4. Contraia o bíceps no topo e desça lentamente.",
  "dicas_seguranca": "Não balance o corpo para ganhar impulso. Mantenha os punhos retos. Controle a fase negativa do movimento.",
  "equipamentos": ["halteres"],
  "tipo_movimento": "isolamento",
  "tags": ["braços", "biceps", "halteres", "isolamento", "basico"]
}
```

### Exemplo 3: Puxada Aberta no Pulley

```json
{
  "nome_exercicio": "Puxada Aberta no Pulley",
  "grupo_muscular": "Latíssimo do Dorso (principal), Bíceps, Romboides, Trapézio (secundários)",
  "musculo_primario": "Costas",
  "modo_execucao": "1. Sente-se no banco e ajuste o apoio das coxas. 2. Segure a barra com as mãos afastadas (pegada aberta). 3. Puxe a barra até a altura do peito, contraindo as escápulas. 4. Retorne lentamente à posição inicial, estendendo os braços.",
  "dicas_seguranca": "Evite balançar o tronco. Não puxe a barra atrás da nuca. Mantenha o core ativado.",
  "equipamentos": ["cabo", "barra", "banco"],
  "tipo_movimento": "composto",
  "tags": ["costas", "pull", "pulley", "maquina", "superior", "intermediario"]
}
```

---

## Fluxo de Respota a Falhas

```
1. Chamada inicial com SYSTEM_PROMPT
   ├── Sucesso → parse JSON → validar campos obrigatórios → retornar
   └── Falha (JSON inválido) →
       2. Re-tentar com SYSTEM_PROMPT + FEW_SHOT_EXAMPLE
          ├── Sucesso → retornar
          └── Falha →
              3. Usar fallback: extrair apenas nome do arquivo + tags mínimas
              4. Logar warning e continuar
```

### Validações pós-prompt

| Condição | Ação |
|----------|------|
| `nome_exercicio` vazio ou ausente | Usar `file_name` como fallback |
| `musculo_primario` vazio | Extrair da primeira parte de `grupo_muscular` |
| `equipamentos` vazio ou ausente | Tentar extrair de `tags` ou `nome_exercicio` |
| `modo_execucao` sem numeração | Adicionar numeração automaticamente |
| `tipo_movimento` fora dos valores esperados | Classificar por heurística (composto se >1 grupo muscular) |

---

## Recomendações por Modelo

| Modelo | Tamanho máximo do prompt | Melhor abordagem |
|--------|-------------------------|------------------|
| GPT-4o | 128k tokens | GIF completo + system prompt completo |
| GPT-4o-mini | 128k tokens | GIF completo + system prompt completo | 
| Gemini 2.5 Flash | 1M tokens | GIF completo via upload + response_mime_type |
| Gemini 2.5 Pro | 1M tokens | GIF completo via upload + response_mime_type |
| Llama 3.2 Vision (11B) | 128k tokens | 3 frames JPEG + system prompt reduzido |
| LLaVA (7B/13B) | 4k tokens | 3 frames JPEG + prompt enxuto + few-shot |

### Ajustes para modelos locais pequenos

Modelos locais com contexto limitado podem se beneficiar de:

1. **Prompt reduzido**: Remover a lista de valores controlados, deixar apenas o schema
2. **Few-shot incluído**: Adicionar 1 example no user message
3. **Instrução explícita**: "Responda APENAS com o JSON, sem texto antes ou depois"
4. **Temperatura mais baixa**: Usar `temperature=0.1` para maior consistência

---

## Variáveis de Ambiente Relacionadas

| Variável | Impacto no Prompt |
|----------|-------------------|
| `AI_RATE_LIMIT` | Controla pausas entre chamadas (respeita rate limits da API) |
| `AI_MODE=local` | Ativa extração de 3 frames e chamada via httpx |
| `AI_MODEL` | Escolhe o modelo (altera capacidade de seguir o schema JSON) |
| `AI_PROVIDER` | Define se usa `response_format=json_object` ou `response_mime_type` |
