import os
import zipfile


def compress_project():
    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_zip = os.path.join(
        os.path.dirname(source_dir),
        "IES_Abastos_2025-26_Proyecto_IA_Big_Data_8IA_Daniel_Porras_Morales.zip"
    )

    # Let's define the exclusion patterns
    # We ignore node_modules, .git, __pycache__, virtual environments, and caches
    exclude_dirs = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".ipynb_checkpoints",
        "dist",
        "build",
    }

    exclude_files = {".eslintcache", ".DS_Store", "thumbs.db"}

    print(f"Iniciando la compresión de '{source_dir}'...")
    print(f"Archivo de salida: '{target_zip}'\n")

    count = 0
    total_size = 0

    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modificamos dirs in-place para que os.walk no entre en directorios excluidos
            # Esto acelera enormemente la compresión y evita recorrer node_modules
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if (
                    file in exclude_files
                    or file.endswith(".zip")
                    or file == "compress_project.py"
                ):
                    continue

                full_path = os.path.join(root, file)
                # Obtenemos la ruta relativa con respecto a la carpeta padre de mercaintelligence
                # Queremos que la estructura dentro del zip comience con 'mercaintelligence/...'
                relative_path = os.path.relpath(
                    full_path, start=os.path.dirname(source_dir)
                )

                # Reemplazamos barras invertidas por barras inclinadas para compatibilidad en zip
                archive_name = relative_path.replace(os.sep, "/")

                # Comprimir el archivo
                zipf.write(full_path, archive_name)
                file_size = os.path.getsize(full_path)
                total_size += file_size
                count += 1

    print("\n¡Compresión completada con éxito!")
    print(f"Total de archivos comprimidos: {count}")
    print(
        f"Tamaño total de los archivos (sin comprimir): {total_size / (1024 * 1024):.2f} MB"
    )
    print(f"Ubicación del archivo zip: '{target_zip}'")


if __name__ == "__main__":
    compress_project()
