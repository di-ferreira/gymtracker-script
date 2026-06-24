import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em biomecânica, cinesiologia e exercícios físicos.
Sua função é analisar imagens/GIFs de exercícios e retornar informações estruturadas.

Analise o GIF (ou seus frames) e o nome do arquivo para identificar o exercício.
Retorna APENAS um objeto JSON válido, sem markdown, sem comentários, sem texto extra:

{
  "nome_exercicio": "Nome padronizado e comercial do exercício em português (ex: Agachamento Livre)",
  "grupo_muscular": "Descrição textual dos músculos principais e secundários ativados",
  "musculo_primario": "Nome do grupo muscular principal (ex: Quadríceps, Peitoral, Costas, Glúteos, Ombros, Bíceps, Tríceps, Abdômen, Panturrilha, Trapézio, Antebraço, Posterior de Coxa)",
  "modo_execucao": "Passo a passo detalhado de como realizar o movimento corretamente, numerando cada etapa (1. ..., 2. ..., etc.)",
  "dicas_seguranca": "Alertas sobre postura, erros comuns a evitar e recomendações de segurança",
  "equipamentos": ["Lista dos equipamentos utilizados (ex: halteres, barra, banco, máquina, cabo, elástico, smith, bola, step, kettlebell, peso corporal)"],
  "tipo_movimento": "Tipo de movimento: composto, isolamento, funcional, calistenia",
  "dificuldade": "Nível de dificuldade: iniciante, intermediario, avancado, expert",
  "exercicios_alternativos": ["Lista de nomes de exercícios similares ou alternativos (ex: Agachamento Frontal, Leg Press)"],
  "tags": ["tag1", "tag2", "tag3"]
}

Use tags relevantes como: pernas, costas, peito, ombros, braços, abdomen, gluteos,
quadriceps, posterior, costa, superior, inferior, fullbody, hipertrofia, resistencia,
calistenia, funcional, maquina, halteres, barra, cabo, elastico, smith, casa, academia,
basico, intermediario, avancado."""

FEW_SHOT_EXAMPLES: List[Dict[str, Any]] = [
    {
        "nome_exercicio": "Agachamento Livre",
        "grupo_muscular": "Quadríceps (principal), Glúteos Máximos, Posterior de Coxa, Eretores da Espinha (secundários)",
        "musculo_primario": "Quadríceps",
        "modo_execucao": "1. Posicione a barra sobre os ombros, atrás do pescoço. 2. Mantenha os pés na largura dos ombros. 3. Desça flexionando joelhos e quadris até as coxas ficarem paralelas ao chão. 4. Expire e suba voltando à posição inicial.",
        "dicas_seguranca": "Mantenha a coluna neutra durante todo o movimento. Não deixe os joelhos ultrapassarem a ponta dos pés. Evite curvar as costas.",
        "equipamentos": ["barra", "anilhas"],
        "tipo_movimento": "composto",
        "dificuldade": "intermediario",
        "exercicios_alternativos": ["Agachamento Frontal", "Leg Press", "Agachamento Sumô"],
        "tags": ["pernas", "quadriceps", "gluteos", "agachamento", "barra", "basico"],
    },
    {
        "nome_exercicio": "Rosca Direta com Halteres",
        "grupo_muscular": "Bíceps Braquial (principal), Braquial, Braquiorradial (secundários)",
        "musculo_primario": "Bíceps",
        "modo_execucao": "1. Em pé, segure um halter em cada mão com as palmas voltadas para frente. 2. Mantenha os cotovelos fixos ao lado do corpo. 3. Flexione os cotovelos elevando os halteres em direção aos ombros. 4. Contraia o bíceps no topo e desça lentamente.",
        "dicas_seguranca": "Não balance o corpo para ganhar impulso. Mantenha os punhos retos. Controle a fase negativa do movimento.",
        "equipamentos": ["halteres"],
        "tipo_movimento": "isolamento",
        "dificuldade": "iniciante",
        "exercicios_alternativos": ["Rosca Martelo", "Rosca Scott", "Rosca Concentrada"],
        "tags": ["braços", "biceps", "halteres", "isolamento", "basico"],
    },
    {
        "nome_exercicio": "Puxada Aberta no Pulley",
        "grupo_muscular": "Latíssimo do Dorso (principal), Bíceps, Romboides, Trapézio (secundários)",
        "musculo_primario": "Costas",
        "modo_execucao": "1. Sente-se no banco e ajuste o apoio das coxas. 2. Segure a barra com as mãos afastadas (pegada aberta). 3. Puxe a barra até a altura do peito, contraindo as escápulas. 4. Retorne lentamente à posição inicial, estendendo os braços.",
        "dicas_seguranca": "Evite balançar o tronco. Não puxe a barra atrás da nuca. Mantenha o core ativado.",
        "equipamentos": ["cabo", "barra", "banco"],
        "tipo_movimento": "composto",
        "dificuldade": "intermediario",
        "exercicios_alternativos": ["Remada Baixa", "Puxada Fechada", "Barra Fixa"],
        "tags": ["costas", "pull", "pulley", "maquina", "superior", "intermediario"],
    },
]

VALID_MUSCLE_GROUPS = {
    "quadríceps", "peitoral", "costas", "glúteos", "ombros",
    "bíceps", "tríceps", "abdômen", "panturrilha", "trapézio",
    "antebraço", "posterior de coxa",
}

VALID_MOVEMENT_TYPES = {"composto", "isolamento", "funcional", "calistenia"}

VALID_DIFFICULTY_LEVELS = {"iniciante", "intermediario", "avancado", "expert"}

REQUIRED_FIELDS = [
    "nome_exercicio",
    "musculo_primario",
    "modo_execucao",
    "dicas_seguranca",
    "equipamentos",
    "tipo_movimento",
    "tags",
]


class PromptBuilder:
    """Monta, valida e recupera prompts para análise de exercícios com IA."""

    @staticmethod
    def build_system_prompt(include_few_shot: bool = False) -> str:
        if not include_few_shot:
            return SYSTEM_PROMPT

        prompt = SYSTEM_PROMPT + "\n\n## Exemplos de respostas corretas:\n"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
            prompt += f"\n### Exemplo {i}:\n"
            prompt += f'Arquivo: "{ex["nome_exercicio"]}"\n'
            prompt += json.dumps(ex, ensure_ascii=False, indent=2) + "\n"
        return prompt

    @staticmethod
    def build_user_message(file_name: str) -> str:
        return (
            f"Analise o exercício no arquivo: {file_name}\n\n"
            f"Retorne APENAS o JSON, sem markdown, sem texto extra."
        )

    @staticmethod
    def validate_response(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for field in REQUIRED_FIELDS:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Campo obrigatório ausente ou vazio: {field}")
            elif isinstance(value, list) and len(value) == 0:
                if field == "equipamentos":
                    errors.append("Lista de equipamentos vazia")
                elif field == "tags":
                    errors.append("Lista de tags vazia")

        muscle = data.get("musculo_primario", "")
        if muscle and muscle.strip().lower() not in VALID_MUSCLE_GROUPS:
            errors.append(f"musculo_primario inválido: '{muscle}'")

        movement = data.get("tipo_movimento", "")
        if movement and movement.strip().lower() not in VALID_MOVEMENT_TYPES:
            errors.append(f"tipo_movimento inválido: '{movement}'")

        return len(errors) == 0, errors

    @staticmethod
    def repair_partial_response(
        data: Dict[str, Any],
        file_name: str = "",
    ) -> Dict[str, Any]:
        repaired = dict(data)

        if not repaired.get("nome_exercicio"):
            repaired["nome_exercicio"] = file_name.replace("_", " ").replace("-", " ").title() if file_name else "Exercício Não Identificado"

        if not repaired.get("musculo_primario"):
            raw = repaired.get("grupo_muscular", "")
            first_word = raw.split(",")[0].split("(")[0].strip()
            if first_word.lower() in VALID_MUSCLE_GROUPS:
                repaired["musculo_primario"] = first_word
            else:
                repaired["musculo_primario"] = "Outros"

        if not repaired.get("equipamentos"):
            extracted: set[str] = set()
            for tag in repaired.get("tags", []):
                tag_lower = tag.lower().strip()
                if tag_lower in {"halteres", "barra", "maquina", "cabo", "elastico",
                                  "smith", "bola", "step", "kettlebell", "banco"}:
                    extracted.add(tag_lower)
            name_lower = repaired.get("nome_exercicio", "").lower()
            for word in ["halteres", "barra", "cabo", "maquina", "smith", "kettlebell", "bola", "step"]:
                if word in name_lower:
                    extracted.add(word)
            if not extracted:
                extracted.add("peso corporal")
            repaired["equipamentos"] = list(extracted)

        if not repaired.get("tipo_movimento"):
            repaired["tipo_movimento"] = "composto"

        if not repaired.get("tags"):
            repaired["tags"] = [repaired.get("musculo_primario", "geral").lower()]

        if not repaired.get("modo_execucao"):
            repaired["modo_execucao"] = "1. Execute o movimento conforme demonstrado na imagem."

        if not repaired.get("dicas_seguranca"):
            repaired["dicas_seguranca"] = "Consulte um profissional de educação física para orientação adequada."

        if not repaired.get("dificuldade"):
            repaired["dificuldade"] = "intermediario"

        if not repaired.get("exercicios_alternativos"):
            repaired["exercicios_alternativos"] = []

        return repaired

    @staticmethod
    def fallback_from_filename(file_name: str) -> Dict[str, Any]:
        cleaned = file_name.replace("_", " ").replace("-", " ").replace("(", "").replace(")", "")
        name = cleaned.strip().title()
        return PromptBuilder.repair_partial_response(
            {"nome_exercicio": name},
            file_name=file_name,
        )

    @staticmethod
    def format_few_shot_block(count: int = 1) -> str:
        block = "\n## Exemplos de respostas corretas:\n"
        for i, ex in enumerate(FEW_SHOT_EXAMPLES[:count], 1):
            block += f"\n### Exemplo {i}:\n"
            block += f'Arquivo: "{ex["nome_exercicio"]}"\n'
            block += json.dumps(ex, ensure_ascii=False, indent=2) + "\n"
        return block
