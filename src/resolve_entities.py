from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from copy import deepcopy

def normalize_name(name: str) -> str:
    prefixes = ["dr", "mr", "mrs", "ms", "prof", "sir"]
    name = name.lower().strip()
    parts = name.split()
    if parts and parts[0].rstrip(".") in prefixes:
        parts = parts[1:]
    return " ".join(parts)

def merge_entities(entities: List[Dict], sim_threshold: float = 0.8, log_merges: bool = True) -> Tuple[List[Dict], Dict[str, str]]:
    resolved_map: Dict[str, str] = {}
    canonical_entities: List[Dict] = []

    for ent in entities:
        ent_name_norm = normalize_name(ent["name"])
        matched = None

        for canon in canonical_entities:
            canon_name_norm = normalize_name(canon["name"])
            canon_aliases_norm = [normalize_name(a) for a in canon.get("aliases", [])]

            if ent_name_norm == canon_name_norm or ent_name_norm in canon_aliases_norm:
                matched = canon
                sim = 1.0
                break

            sim = SequenceMatcher(None, ent_name_norm, canon_name_norm).ratio()
            if sim >= sim_threshold:
                matched = canon
                break

        if matched:
            if "aliases" not in matched:
                matched["aliases"] = []
            if ent["name"] != matched["name"] and ent["name"] not in matched["aliases"]:
                matched["aliases"].append(ent["name"])
            resolved_map[ent["id"]] = matched["id"]
            if log_merges:
                print(f"[Entity Resolution] Merged '{ent['name']}' -> '{matched['name']}' (sim={sim:.2f})")
        else:
            # Create a new canonical entity explicitly
            new_canon = {"id": ent["id"], "name": ent["name"], "aliases": []}
            canonical_entities.append(new_canon)
            resolved_map[ent["id"]] = new_canon["id"]

    return canonical_entities, resolved_map

def remap_relationships(relationships: List[Dict], resolved_map: Dict[str, str], log: bool = False) -> List[Dict]:
    resolved_relationships: List[Dict] = []
    seen: set = set()
    for rel in relationships:
        src = resolved_map.get(rel["source"], rel["source"])
        tgt = resolved_map.get(rel["target"], rel["target"])
        rel_key = (src, rel["relation"], tgt)
        if rel_key not in seen:
            resolved_relationships.append({
                "source": src, "relation": rel["relation"], "target": tgt,
                "evidence_span": rel.get("evidence_span", "")
            })
            seen.add(rel_key)
        elif log:
            print(f"[Relationship Resolution] Duplicate removed: {rel_key}")
    return resolved_relationships

def finalize_entities_and_relationships(entities: List[Dict], relationships: List[Dict], log: bool = True) -> Tuple[List[Dict], List[Dict]]:
    entities_copy = deepcopy(entities)
    relationships_copy = deepcopy(relationships)
    canonical_entities, resolved_map = merge_entities(entities_copy, log_merges=log)
    valid_ids = {e["id"] for e in canonical_entities}
    filtered_relationships = [rel for rel in relationships_copy if rel["source"] in valid_ids and rel["target"] in valid_ids]
    final_relationships = remap_relationships(filtered_relationships, resolved_map, log=log)
    return canonical_entities, final_relationships

# ===== Example Usage =====
if __name__ == "__main__":
    entities = [
        {"id": "1", "name": "Watson"},
        {"id": "2", "name": "Dr Watson"},
        {"id": "3", "name": "John"}
    ]
    relationships = [
        {"source": "2", "relation": "works_with", "target": "3", "evidence_span": "text1"},
        {"source": "1", "relation": "works_with", "target": "3", "evidence_span": "text2"}
    ]
    canonical_entities, resolved_relationships = finalize_entities_and_relationships(entities, relationships, log=True)
    print("\nCanonical Entities:")
    for e in canonical_entities:
        print(e)
    print("\nResolved Relationships:")
    for r in resolved_relationships:
        print(r)
