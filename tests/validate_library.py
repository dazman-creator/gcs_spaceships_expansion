import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_DIR = ROOT / "Library" / "Spaceships"
VERSION_FILE = ROOT / "VERSION"
EXPECTED_SCHEMA_VERSION = 5
SUPPORTED_EXTENSIONS = {".gcs", ".body", ".adq", ".adm", ".eqm", ".eqp"}
EXPECTED_FILES = {
    "Basic_Spaceship_Sheet.gcs",
    "Spaceship.body",
    "Spaceships - Chassis.adq",
    "Spaceships - Equipment Modifiers.eqm",
    "Spaceships - Modules.eqp",
    "Spaceships - Trait Modifiers.adm",
}


def load_json(path, errors):
    raw = path.read_text(encoding="utf-8-sig")
    stripped = raw.lstrip()
    if stripped.startswith("<!DOCTYPE html") or stripped.startswith("<html"):
        errors.append(f"{path}: parece HTML salvo do GitHub, nao arquivo GCS raw.")
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: JSON invalido na linha {exc.lineno}, coluna {exc.colno}: {exc.msg}.")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: raiz precisa ser objeto JSON.")
        return None
    return data


def require(condition, errors, message):
    if not condition:
        errors.append(message)


def walk_nodes(rows):
    stack = list(rows)
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            yield node
            stack.extend(node.get("children", []))


def validate_version_file(errors):
    require(VERSION_FILE.exists(), errors, "VERSION nao existe.")
    if not VERSION_FILE.exists():
        return None
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), errors, "VERSION precisa estar no formato X.Y.Z.")
    return version


def validate_common(path, data, errors):
    require(data.get("version") == EXPECTED_SCHEMA_VERSION, errors, f"{path}: version precisa ser {EXPECTED_SCHEMA_VERSION}.")


def validate_body(path, data, errors):
    validate_common(path, data, errors)
    require(data.get("name") == "Spaceship", errors, f"{path}: name esperado: Spaceship.")
    require(data.get("roll") == "3d", errors, f"{path}: roll esperado: 3d.")
    locations = data.get("locations")
    require(isinstance(locations, list), errors, f"{path}: locations precisa ser lista.")
    if not isinstance(locations, list):
        return

    expected = {
        "front": ("3-8", 6),
        "center": ("9-12", 6),
        "rear": ("13-18", 6),
        "core": ("-", 2),
    }
    seen = {}
    for location in locations:
        if not isinstance(location, dict):
            errors.append(f"{path}: location precisa ser objeto.")
            continue
        seen[location.get("id")] = location
        require("choice_name" in location, errors, f"{path}: location {location.get('id')} sem choice_name.")
        require("table_name" in location, errors, f"{path}: location {location.get('id')} sem table_name.")
        require(isinstance(location.get("slots"), int), errors, f"{path}: location {location.get('id')} sem slots numerico.")
        require("calc" in location and isinstance(location["calc"], dict), errors, f"{path}: location {location.get('id')} sem calc.")

    require(set(seen) == set(expected), errors, f"{path}: locations esperadas {sorted(expected)}, recebeu {sorted(seen)}.")
    for location_id, (roll_range, slots) in expected.items():
        location = seen.get(location_id)
        if not location:
            continue
        require(location.get("slots") == slots, errors, f"{path}: {location_id} deve ter {slots} slots.")
        actual_range = location.get("calc", {}).get("roll_range")
        require(actual_range == roll_range, errors, f"{path}: {location_id} roll_range deve ser {roll_range}, recebeu {actual_range}.")

    total_slots = sum(location.get("slots", 0) for location in locations if isinstance(location, dict))
    require(total_slots == 20, errors, f"{path}: total de slots deve ser 20, recebeu {total_slots}.")


def validate_trait_list(path, data, errors):
    validate_common(path, data, errors)
    require(data.get("type") == "trait_list", errors, f"{path}: type esperado: trait_list.")
    rows = data.get("rows")
    require(isinstance(rows, list) and rows, errors, f"{path}: rows precisa ser lista nao vazia.")
    if not isinstance(rows, list):
        return
    for row in rows:
        require(row.get("type") == "trait_container", errors, f"{path}: linha raiz precisa ser trait_container.")
        require(row.get("id"), errors, f"{path}: trait_container sem id.")
        require(row.get("name"), errors, f"{path}: trait_container sem name.")
        require(isinstance(row.get("children"), list) and row["children"], errors, f"{path}: trait_container sem children.")

    for node in walk_nodes(rows):
        node_type = node.get("type")
        if node_type in {"trait", "trait_container"}:
            require(node.get("name"), errors, f"{path}: {node_type} sem name.")
        if node_type == "trait":
            has_points = any(key in node for key in ("base_points", "points_per_level", "calc"))
            require(has_points, errors, f"{path}: trait {node.get('name')} sem campos de pontos/calculo.")


def validate_trait_modifiers(path, data, errors):
    validate_common(path, data, errors)
    rows = data.get("rows")
    require(isinstance(rows, list), errors, f"{path}: rows precisa ser lista.")
    if not isinstance(rows, list):
        return
    require("type" not in data, errors, f"{path}: .adm de trait nao deve declarar type no topo.")
    for row in rows:
        require(isinstance(row, dict), errors, f"{path}: row precisa ser objeto.")
        require("children" not in row, errors, f"{path}: .adm de trait deve colocar modificadores direto em rows.")
        require(row.get("id"), errors, f"{path}: modificador sem id.")
        require(row.get("name"), errors, f"{path}: modificador sem name.")
        require("cost_adj" in row, errors, f"{path}: modificador {row.get('name')} sem cost_adj.")
        require("cost" not in row, errors, f"{path}: modificador {row.get('name')} usa cost; use cost_adj.")


def validate_equipment_modifiers(path, data, errors):
    validate_common(path, data, errors)
    require(data.get("type") == "eqp_modifier_list", errors, f"{path}: type esperado: eqp_modifier_list.")
    rows = data.get("rows")
    require(isinstance(rows, list) and rows, errors, f"{path}: rows precisa ser lista nao vazia.")
    if not isinstance(rows, list):
        return
    for row in rows:
        require(row.get("type") == "eqp_modifier_container", errors, f"{path}: linha raiz precisa ser eqp_modifier_container.")
        require(row.get("name"), errors, f"{path}: eqp_modifier_container sem name.")
        require(isinstance(row.get("children"), list), errors, f"{path}: eqp_modifier_container sem children.")
        for child in row.get("children", []):
            require(child.get("type") == "eqp_modifier", errors, f"{path}: child precisa ser eqp_modifier.")
            require(child.get("id"), errors, f"{path}: eqp_modifier sem id.")
            require(child.get("name"), errors, f"{path}: eqp_modifier sem name.")


def validate_equipment_list(path, data, errors):
    validate_common(path, data, errors)
    rows = data.get("rows")
    require(isinstance(rows, list) and rows, errors, f"{path}: rows precisa ser lista nao vazia.")
    if not isinstance(rows, list):
        return
    descriptions = []
    for node in walk_nodes(rows):
        if "description" in node:
            descriptions.append(str(node["description"]))
        if node.get("type") == "equipment":
            require(node.get("id"), errors, f"{path}: equipment sem id.")
            require(node.get("description"), errors, f"{path}: equipment sem description.")

    full_text = "\n".join(descriptions)
    for sm in range(5, 16):
        require(f"SM+{sm}" in full_text, errors, f"{path}: nenhum modulo para SM+{sm}.")


def validate_character_sheet(path, data, errors):
    validate_common(path, data, errors)
    require(isinstance(data.get("settings"), dict), errors, f"{path}: settings precisa existir.")
    require(isinstance(data.get("profile"), dict), errors, f"{path}: profile precisa existir.")
    require(isinstance(data.get("equipment"), list), errors, f"{path}: equipment precisa ser lista.")


def validate_library(errors):
    require(LIBRARY_DIR.exists(), errors, f"{LIBRARY_DIR}: pasta Library/Spaceships nao encontrada.")
    if not LIBRARY_DIR.exists():
        return

    files = [path for path in LIBRARY_DIR.rglob("*") if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS]
    names = {path.name for path in files}
    missing = EXPECTED_FILES - names
    require(not missing, errors, f"Arquivos esperados ausentes: {sorted(missing)}.")

    validators = {
        ".body": validate_body,
        ".adq": validate_trait_list,
        ".adm": validate_trait_modifiers,
        ".eqm": validate_equipment_modifiers,
        ".eqp": validate_equipment_list,
        ".gcs": validate_character_sheet,
    }
    for path in files:
        data = load_json(path, errors)
        if data is None:
            continue
        validators[path.suffix](path, data, errors)


def main():
    errors = []
    gcs_version = validate_version_file(errors)
    validate_library(errors)
    if errors:
        print("Validacao falhou:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"OK: VERSION={gcs_version} e arquivos da Library/Spaceships validos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
