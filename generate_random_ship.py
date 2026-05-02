import json
import random
import argparse
import os

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_item_by_name(library, name_part):
    found = []
    for row in library.get("rows", []):
        if "children" in row:
            for child in row["children"]:
                desc = child.get("description", "")
                if name_part.lower() in desc.lower():
                    found.append(child)
    return found

def get_random_module(library, sm, keywords, location):
    # keywords is a list of strings to match
    options = []
    for row in library.get("rows", []):
        if "children" in row:
            for child in row["children"]:
                desc = child.get("description", "")
                tags = child.get("tags", [])
                
                # Check SM
                if f"SM+{sm}" not in desc:
                    continue
                    
                # Check location
                if location not in tags and "Hull" not in tags and "Armor" not in tags:
                    # Some items might not strictly have the location tag but we added Front/Center/Rear/Core to all
                    if location not in tags and not any(l in tags for l in ["Front", "Center", "Rear", "Core"]):
                        pass # Has no location restriction
                    else:
                        continue
                
                # Check keywords (OR logic)
                for kw in keywords:
                    if kw.lower() in desc.lower() or any(kw.lower() in t.lower() for t in tags):
                        options.append(child)
                        break
    if options:
        return random.choice(options)
    return None

def main():
    parser = argparse.ArgumentParser(description="GCS Random Spaceship Generator")
    parser.add_argument("--sm", type=int, choices=range(5, 16), default=8, help="Size Modifier (5-15)")
    parser.add_argument("--shipclass", type=str, choices=["freighter", "warship", "explorer"], default="freighter", help="Ship Class")
    args = parser.parse_args()
    
    base_dir = r"C:\Users\User\GCS\User Library\Spaceships"
    
    # 1. Load Boilerplate and DB
    template = load_json(os.path.join(base_dir, "Basic_Spaceship_Sheet.gcs"))
    modules_db = load_json(os.path.join(base_dir, "Spaceships - Modules.eqp"))
    chassis_db = load_json(os.path.join(base_dir, "Spaceships - Chassis.adq"))
    body_db = load_json(os.path.join(base_dir, "Spaceship.body"))
    
    # 2. Setup Base Info
    prefixes = ["USS", "VSS", "ISV", "HMS", "FSS"]
    names = ["Star-Skipper", "Leviathan", "Voyager", "Nomad", "Centurion", "Stardust", "Eclipse", "Horizon", "Pioneer", "Vanguard"]
    ship_name = f"{random.choice(prefixes)} {random.choice(names)}"
    
    template["profile"]["name"] = ship_name
    template["profile"]["player_name"] = "Random Generator"
    
    # Check if 'body' exists in settings, else create
    if "body" not in template["settings"]:
        template["settings"]["body"] = {}
    
    template["settings"]["body"]["name"] = body_db["name"]
    template["settings"]["body"]["roll"] = body_db["roll"]
    template["settings"]["body"]["locations"] = body_db["locations"]
    
    # 3. Add Chassis
    chassis_item = None
    for row in chassis_db.get("rows", []):
        if f"SM+{args.sm}" in row.get("name", ""):
            chassis_item = row
            break
            
    if chassis_item:
        if "traits" not in template:
            template["traits"] = []
        template["traits"].append(chassis_item)
        
    # 4. Build Equipment Slots
    equipment = []
    
    locs = ["Front", "Center", "Rear", "Core"]
    slots = {"Front": 6, "Center": 6, "Rear": 6, "Core": 2}
    
    # Logic for archetypes
    # Returns a keyword to search for
    def pick_module_type(ship_class, loc, slot_num):
        if loc == "Front":
            if slot_num == 0: return ["Front Armor"]
            if slot_num == 1: return ["Control Room"]
            if ship_class == "freighter":
                if slot_num == 2: return ["Habitat"]
                return ["Cargo Hold"]
            elif ship_class == "warship":
                if slot_num in [2,3]: return ["Major Battery", "Medium Battery"]
                if slot_num == 4: return ["Force Screen"]
                return ["Habitat"]
            elif ship_class == "explorer":
                if slot_num == 2: return ["Science Array"]
                if slot_num == 3: return ["Habitat"]
                return ["Cargo Hold"]
                
        if loc == "Center":
            if slot_num == 0: return ["Center Armor"]
            if ship_class == "freighter":
                if slot_num == 1: return ["Passenger"]
                return ["Cargo Hold", "Fuel Tank"]
            elif ship_class == "warship":
                if slot_num in [1,2]: return ["Major Battery", "Medium Battery", "Secondary Battery"]
                return ["Fuel Tank"]
            elif ship_class == "explorer":
                if slot_num == 1: return ["Habitat"]
                if slot_num == 2: return ["Hangar"]
                return ["Fuel Tank", "Cargo Hold"]
                
        if loc == "Rear":
            if slot_num == 0: return ["Rear Armor"]
            if slot_num in [1, 2]: return ["Engine", "Drive", "Rocket"] # propulsion
            if ship_class == "freighter":
                if slot_num == 3: return ["Hangar"]
                return ["Cargo Hold", "Fuel Tank"]
            elif ship_class == "warship":
                if slot_num == 3: return ["Engine", "Drive"]
                return ["Fuel Tank", "Battery"]
            elif ship_class == "explorer":
                return ["Fuel Tank", "Cargo Hold", "Engine"]
                
        if loc == "Core":
            if slot_num == 0: return ["Reactor", "Power Plant"]
            if ship_class == "warship": return ["Reactor", "Power Plant"]
            if ship_class == "explorer": return ["Stardrive"]
            return ["Engine Room", "Reactor"]
            
        return ["Cargo Hold"]

    for loc in locs:
        container = {
            "type": "equipment_container",
            "description": f"{loc} Hull Section",
            "children": []
        }
        
        for i in range(slots[loc]):
            kws = pick_module_type(args.shipclass, loc, i)
            mod = get_random_module(modules_db, args.sm, kws, loc)
            if not mod:
                # fallback
                mod = get_random_module(modules_db, args.sm, ["Cargo Hold"], loc)
            
            if mod:
                container["children"].append(mod)
                
        equipment.append(container)
        
    template["equipment"] = equipment
    
    # 5. Output
    out_name = f"{ship_name.replace(' ', '_')}.gcs"
    out_path = os.path.join(base_dir, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=4)
        
    print(f"Nave gerada com sucesso: {out_path}")

if __name__ == "__main__":
    main()
