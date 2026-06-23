import os
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

def move_to_processed(file_path: str | Path, processed_dirname: str = "processados") -> Path:
    """
    Move o arquivo atual para uma pasta de backup isolada após o processamento com sucesso.
    Evita colisões se o arquivo já existir no destino criando um sufixo numérico.
    
    :param file_path: Caminho do arquivo original que foi processado
    :param processed_dirname: Nome da pasta onde ficarão os arquivos finalizados
    :return: Path do arquivo em seu novo destino
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado para movimentação: {file_path}")

    # Define a pasta destino baseada na raiz do arquivo atual
    destination_dir = file_path.parent / processed_dirname
    destination_dir.mkdir(parents=True, exist_ok=True)
    
    destination_path = destination_dir / file_path.name
    
    # Tratamento de colisão de nomes (Evita sobrescrever arquivos com o mesmo nome)
    counter = 1
    base_name = file_path.stem
    extension = file_path.suffix
    
    while destination_path.exists():
        destination_path = destination_dir / f"{base_name}_{counter}{extension}"
        counter += 1

    # Move o arquivo fisicamente
    try:
        shutil.move(str(file_path), str(destination_path))
        logger.info(f"Arquivo movido com sucesso para: {destination_path}")
        return destination_path
    except Exception as e:
        logger.error(f"Falha ao mover arquivo {file_path.name}: {str(e)}")
        raise e