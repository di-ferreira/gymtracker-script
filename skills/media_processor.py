from typing import List
from PIL import Image
from pathlib import Path

JPEG_QUALITY = 60
MAX_DIMENSION = 512


def extract_gif_frames(
    gif_path: str | Path, max_frames: int = 3, max_dimension: int = MAX_DIMENSION
) -> List[Image.Image]:
    gif_path = Path(gif_path)
    if not gif_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {gif_path}")

    frames: List[Image.Image] = []

    with Image.open(gif_path) as im:
        total_frames = 0
        while True:
            try:
                im.seek(total_frames)
                total_frames += 1
            except EOFError:
                break

        if total_frames <= max_frames:
            indices = list(range(total_frames))
        else:
            indices = [
                int(i * (total_frames - 1) / (max_frames - 1))
                for i in range(max_frames)
            ]

        for index in indices:
            im.seek(index)
            frame_rgba = im.convert("RGBA")
            background = Image.new("RGBA", frame_rgba.size, (255, 255, 255, 255))
            alpha_composite = Image.alpha_composite(background, frame_rgba)
            rgb = alpha_composite.convert("RGB")

            if max_dimension and (rgb.width > max_dimension or rgb.height > max_dimension):
                ratio = min(max_dimension / rgb.width, max_dimension / rgb.height)
                new_size = (int(rgb.width * ratio), int(rgb.height * ratio))
                rgb = rgb.resize(new_size, Image.LANCZOS)

            frames.append(rgb)

    return frames