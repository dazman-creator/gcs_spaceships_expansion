import argparse
import json
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATOR_SCRIPT = ROOT / "generate_random_ship.py"
LIBRARY_DIR = ROOT / "Library" / "Spaceships"


def extract_equipment(node, result):
    if node.get("type") == "equipment":
        result.append(node)
    for child in node.get("children", []):
        extract_equipment(child, result)


def validate_generated_ship(path):
    errors = []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    equipment = []
    for eq_container in data.get("equipment", []):
        extract_equipment(eq_container, equipment)

    slot_count = sum(len(eq_container.get("children", [])) for eq_container in data.get("equipment", []))
    if slot_count != 20:
        errors.append(f"{path.name}: possui {slot_count} slots em vez de 20.")

    unequipped = [eq for eq in equipment if not eq.get("equipped", False)]
    if unequipped:
        errors.append(f"{path.name}: encontrou {len(unequipped)} equipamentos com 'equipped' ausente ou falso.")

    valid_locations = {"front", "center", "rear", "core"}
    for eq in equipment:
        for feature in eq.get("features", []):
            if feature.get("type") == "dr_bonus" and feature.get("location") not in valid_locations:
                errors.append(
                    f"{path.name}: armadura {eq.get('description')} tem location invalida: {feature.get('location')}"
                )

    ids = [eq.get("id") for eq in equipment if "id" in eq]
    if len(ids) != len(set(ids)):
        errors.append(f"{path.name}: possui IDs duplicados nos equipamentos.")

    for eq in equipment:
        for weapon in eq.get("weapons", []):
            if "id" not in weapon:
                errors.append(f"{path.name}: arma sem ID no equipamento {eq.get('description')}.")

    return errors


def run_tests(count):
    print(f"Iniciando a geracao de {count} naves de teste...")
    classes = ["freighter", "warship", "explorer"]
    errors = []
    start_time = time.time()

    with tempfile.TemporaryDirectory(prefix="gcs_spaceships_test_") as out_dir:
        out_path = Path(out_dir)
        for i in range(count):
            sm = random.randint(5, 15)
            ship_class = random.choice(classes)
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR_SCRIPT),
                    "--sm",
                    str(sm),
                    "--shipclass",
                    ship_class,
                    "--library-dir",
                    str(LIBRARY_DIR),
                    "--outdir",
                    str(out_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"Gerador falhou para SM+{sm}/{ship_class}: {result.stderr.strip()}")
                continue

            if (i + 1) % 25 == 0 or i + 1 == count:
                print(f"Geradas {i + 1}/{count} naves...")

        files = sorted(out_path.glob("*.gcs"))
        if len(files) != count:
            errors.append(f"Esperava {count} arquivos .gcs gerados, encontrei {len(files)}.")

        for path in files:
            try:
                errors.extend(validate_generated_ship(path))
            except Exception as exc:
                errors.append(f"{path.name}: erro ao processar - {exc}")

    print(f"{count} naves geradas em {time.time() - start_time:.2f} segundos.")
    print("\n--- RELATORIO DE AUDITORIA ---")
    if errors:
        print(f"FALHA! Encontrados {len(errors)} erros:")
        for error in errors[:30]:
            print(f"- {error}")
        if len(errors) > 30:
            print(f"... e mais {len(errors) - 30} erros.")
        return 1

    print(f"SUCESSO! Todas as {count} naves foram geradas e validadas sem erro.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate random GCS spaceships and validate their structure.")
    parser.add_argument("--count", type=int, default=50, help="Number of random ships to generate")
    args = parser.parse_args()
    raise SystemExit(run_tests(args.count))


if __name__ == "__main__":
    main()
