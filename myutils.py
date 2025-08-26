# utils.py
from typing import List, Optional, Tuple
import requests
import re
from datetime import datetime
from difflib import SequenceMatcher
import time

def fetch_raw_text(url: str, timeout: int = 30, user_agent: str = "cti-demo/1.0") -> Optional[str]:
    """
    Fetch URL and return decoded text (r.text). Returns None on failure.
    """
    headers = {"User-Agent": user_agent}
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        # ensure we return a str, not bytes
        return r.text
    except requests.RequestException as e:
        print(f"HTTP error fetching {url}: {e}")
        return None



def strip_gutenberg_header_footer(text: str) -> str:
    """
    Remove Project Gutenberg header/footer using robust heuristics.
    If the standard markers are not found, attempt fallback:
    - find first chapter heading (e.g., "CHAPTER I")
    """
    if not isinstance(text, str):
        raise TypeError("strip_gutenberg_header_footer expects a str")

    # try standard Gutenberg markers (DOTALL so .* can match across newlines)
    start_re = re.compile(r"\*\*\* *START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE | re.DOTALL)
    end_re = re.compile(r"\*\*\* *END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.IGNORECASE | re.DOTALL)

    start_match = start_re.search(text)
    if start_match:
        start_idx = start_match.end()
    else:
        # fallback: look for common chapter/section headings (heuristic)
        alt_start = re.search(r"(?:^|\n)(chapter|i\.)\s+[A-Z0-9\.\- ]{2,}", text, re.IGNORECASE)
        start_idx = alt_start.start() if alt_start else 0

    end_match = end_re.search(text)
    if end_match:
        end_idx = end_match.start()
    else:
        # fallback: strip trailing Gutenberg license/footer that often contains "End of Project Gutenberg"
        alt_end = re.search(r"\*\*\* *END OF .{0,80}$", text, re.IGNORECASE | re.DOTALL)
        end_idx = alt_end.start() if alt_end else len(text)

    core = text[start_idx:end_idx].strip()
    return core


def chunk_text(text: str, max_chars: int = 3000, overlap: int = 200) -> List[str]:
    """
    Chunk text into pieces no larger than max_chars (approx), with optional overlap.
    Splits on sentence boundaries where possible.
    If a single sentence is longer than max_chars, it will be included as its own chunk.
    Overlap is now applied with full words (no cutting words in half).
    """
    import re
    from typing import List

    if not isinstance(text, str):
        raise TypeError("chunk_text expects a str")
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    # split by sentence boundary  
    sentences = re.split(r'(?<=[.!?])', text)
    chunks: List[str] = []
    cur = ""

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(cur) + len(s) + 1 <= max_chars:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                chunks.append(cur)
            # if single sentence is longer than max_chars, we still include it alone
            if len(s) > max_chars:
                for i in range(0, len(s), max_chars):
                    part = s[i:i + max_chars]
                    chunks.append(part)
                cur = ""
            else:
                cur = s
    if cur:
        chunks.append(cur)

    # apply overlap using **whole words**
    if overlap and len(chunks) > 1:
        new_chunks: List[str] = []
        for i, c in enumerate(chunks):
            if i == 0:
                new_chunks.append(c)
                continue
            prev = new_chunks[-1]

            # split previous chunk into words
            prev_words = prev.split()
            # take enough words from the end to get at most `overlap` characters
            overlap_words = []
            char_count = 0
            for w in reversed(prev_words):
                if char_count + len(w) + 1 > overlap:
                    break
                overlap_words.insert(0, w)  # prepend to maintain order
                char_count += len(w) + 1  # +1 for space

            overlap_text = " ".join(overlap_words)
            candidate = (overlap_text + " " + c).strip()
            new_chunks.append(candidate)
        chunks = new_chunks

    return chunks



def is_potential_alias(name1, name2, threshold=0.85):
    """Check if two names are likely aliases of each other using fuzzy similarity."""
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio() > threshold


def merge_entities(global_entities, log_merges=True):
    """
    Merge duplicate/variant entities into canonical ones using alias similarity.
    
    Args:
        global_entities (list): [{"id", "name", ...}, ...]
        log_merges (bool): If True, print logs of merges.

    Returns:
        canonical_entities (list): merged list of entities.
        resolved_map (dict): mapping of old IDs -> new canonical IDs.
    """
    resolved_map = {}
    canonical_entities = []

    for ent in global_entities:
        matched = None
        for canon in canonical_entities:
            if (ent["name"].lower() == canon["name"].lower() or 
                ent["name"].lower() in [a.lower() for a in canon.get("aliases", [])] or
                is_potential_alias(ent["name"], canon["name"])):

                matched = canon
                break

        if matched:
            # Add alias if new
            if ent["name"] not in matched["aliases"]:
                matched["aliases"].append(ent["name"])
            if log_merges:
                sim = SequenceMatcher(None, ent["name"].lower(), matched["name"].lower()).ratio()
                print(f"[Entity Resolution] Merged '{ent['name']}' -> '{matched['name']}' (sim={sim:.2f})")
            resolved_map[ent["id"]] = matched["id"]
        else:
            if "aliases" not in ent:
                ent["aliases"] = []
            canonical_entities.append(ent)
            resolved_map[ent["id"]] = ent["id"]

    return canonical_entities, resolved_map


def remap_relationships(global_relationships, resolved_map):
    """Remap relationships to use canonical entity IDs (no recomputation)."""
    resolved_relationships = []
    seen = set()

    for rel in global_relationships:
        src = resolved_map[rel["source"]]
        tgt = resolved_map[rel["target"]]

        rel_key = (src, rel["relation"], tgt)
        if rel_key not in seen:
            resolved_relationships.append({
                "source": src,
                "relation": rel["relation"],
                "target": tgt,
                "evidence_span": rel.get("evidence_span", "")
            })
            seen.add(rel_key)

    return resolved_relationships
