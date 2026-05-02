import os
import sys
import json
import random
import subprocess
import time

def run_tests():
    out_dir = r"C:\Users\User\GCS\User Library\Spaceships\Models\teste"
    generator_script = r"C:\Users\User\GCS\gcs_spaceships_expansion\generate_random_ship.py"
    
    # 1. Generate 500 ships
    print("Iniciando a geração de 500 naves de teste...")
    classes = ["freighter", "warship", "explorer"]
    
    start_time = time.time()
    for i in range(500):
        sm = random.randint(5, 15)
        shipclass = random.choice(classes)
        # Suppress output to keep console clean
        subprocess.run(
            ["python", generator_script, "--sm", str(sm), "--shipclass", shipclass, "--outdir", out_dir],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if (i+1) % 50 == 0:
            print(f"Geradas {i+1}/500 naves...")
            
    print(f"500 naves geradas em {time.time() - start_time:.2f} segundos.")
    
    # 2. Validation
    errors = []
    
    files = [f for f in os.listdir(out_dir) if f.endswith(".gcs")]
    for filename in files:
        filepath = os.path.join(out_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # A. Extract all equipment
            equipments = []
            def extract_eq(node):
                if node.get("type") == "equipment":
                    equipments.append(node)
                if "children" in node:
                    for child in node["children"]:
                        extract_eq(child)
            
            for eq_container in data.get("equipment", []):
                extract_eq(eq_container)
                
            # Test 1: Slots = 20
            # Note: GCS uses containers for front, center, rear, core. 
            # In our generator, we put exact slots inside the 4 containers.
            # But extract_eq extracts all equipments, including nested. 
            # In Spaceships, each main system is a slot. Let's just count the direct children of the 4 containers.
            slot_count = 0
            for eq_container in data.get("equipment", []):
                slot_count += len(eq_container.get("children", []))
            
            if slot_count != 20:
                errors.append(f"{filename}: Possui {slot_count} slots em vez de 20.")
                
            # Test 2: Equipped flag
            unequipped = [eq for eq in equipments if not eq.get("equipped", False)]
            if unequipped:
                errors.append(f"{filename}: Encontrou {len(unequipped)} equipamentos/containers com 'equipped' ausente ou falso.")
                
            # Test 3: dr_bonus location
            valid_locs = ["front", "center", "rear", "core"]
            for eq in equipments:
                for feat in eq.get("features", []):
                    if feat.get("type") == "dr_bonus":
                        if feat.get("location") not in valid_locs:
                            errors.append(f"{filename}: Armadura {eq.get('description')} tem location inválida: {feat.get('location')}")
                            
            # Test 4: Unique IDs
            # ID is not always in node.get("id") if it was wiped, but it should be unique.
            ids = [eq.get("id") for eq in equipments if "id" in eq]
            if len(ids) != len(set(ids)):
                errors.append(f"{filename}: Possui IDs duplicados nos equipamentos.")
                
            # Test 5: Weapon IDs
            for eq in equipments:
                for w in eq.get("weapons", []):
                    if "id" not in w:
                        errors.append(f"{filename}: Arma sem ID encontrada no equipamento: {eq.get('description')}")
                
        except Exception as e:
            errors.append(f"{filename}: Erro ao processar - {str(e)}")
            
    # 3. Report
    print("\n--- RELATÓRIO DE AUDITORIA ---")
    if not errors:
        print(f"SUCESSO ABSOLUTO! Todas as {len(files)} naves foram geradas e validadas sem nenhum erro.")
    else:
        print(f"FALHA! Encontrados {len(errors)} erros:")
        for err in set(errors[:20]): # Print up to 20 unique errors to avoid spam
            print(f"- {err}")
        if len(errors) > 20:
            print(f"... e mais {len(errors) - 20} erros.")
            
if __name__ == "__main__":
    run_tests()
