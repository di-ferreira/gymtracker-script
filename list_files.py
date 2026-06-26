import sys
from pathlib import Path
from collections import defaultdict


def list_files_by_extension(root_path: str, output_file: str = "lista_arquivos.txt"):
    root = Path(root_path)
    if not root.is_dir():
        print(f"Erro: '{root_path}' nao e um diretorio valido.")
        return

    files_by_ext = defaultdict(list)

    for file_path in sorted(root.rglob("*")):
        if file_path.is_file():
            ext = file_path.suffix.lower() or "(sem extensao)"
            files_by_ext[ext].append(file_path)

    counter = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for ext in sorted(files_by_ext.keys()):
            f.write(f"{ext}\n")
            for fp in sorted(files_by_ext[ext]):
                counter += 1
                rel = fp.relative_to(root)
                f.write(f"{counter}. {rel}\n")
            f.write("\n")

    print(f"Lista salva em '{output_file}' com {counter} arquivos.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python list_files.py <caminho> [arquivo_saida.txt]")
        sys.exit(1)
    output = sys.argv[2] if len(sys.argv) > 2 else "lista_arquivos.txt"
    list_files_by_extension(sys.argv[1], output)
