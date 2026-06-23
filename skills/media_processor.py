import os
from typing import List
from PIL import Image
from pathlib import Path

def extract_gif_frames(gif_path: str | Path, max_frames: int = 3) -> List[Image.Image]:
    """
    Abre um arquivo GIF animado e extrai uma quantidade 'max_frames' de frames 
    distribuídos uniformemente ao longo da animação.
    
    :param gif_path: Caminho local para o arquivo .gif
    :param max_frames: Quantidade máxima de frames a ser extraída
    :return: Lista de objetos PIL Image contendo os frames extraídos
    """
    gif_path = Path(gif_path)
    if not gif_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {gif_path}")
        
    frames: List[Image.Image] = []
    
    with Image.open(gif_path) as im:
        # Descobre o total de frames do GIF
        total_frames = 0
        while True:
            try:
                im.seek(total_frames)
                total_frames += 1
            except EOFError:
                break
        
        # Calcula os índices dos frames que serão extraídos de forma uniforme
        if total_frames <= max_frames:
            indices = list(range(total_frames))
        else:
            indices = [int(i * (total_frames - 1) / (max_frames - 1)) for i in range(max_frames)]
        
        # Extrai e converte os frames para RGB (padrão aceito pela maioria das LLMs)
        for index in indices:
            im.seek(index)
            frame_rgba = im.convert("RGBA")
            # Cria fundo branco para manter contraste caso o GIF tenha transparência
            background = Image.new("RGBA", frame_rgba.size, (255, 255, 255, 255))
            alpha_composite = Image.alpha_composite(background, frame_rgba)
            frames.append(alpha_composite.convert("RGB"))
            
    return frames