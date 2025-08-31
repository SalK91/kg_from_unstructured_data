import re
from typing import Optional
import requests
from pathlib import Path
from typing import List



def fetch_raw_text(
    url: str,
    timeout: int = 30,
    user_agent: str = "cti-demo/1.0"
) -> Optional[str]:
    """
    Fetch URL and return decoded text. Returns None on failure.
    """
    headers = {"User-Agent": user_agent}
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"HTTP error fetching {url}: {e}")
        return None


def strip_gutenberg_header_footer(text: str) -> str:
    """
    Remove Project Gutenberg header/footer using robust heuristics.
    """
    if not isinstance(text, str):
        raise TypeError("strip_gutenberg_header_footer expects a str")

    # Standard Gutenberg markers
    start_re = re.compile(
        r"\*\*\* *START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL
    )
    end_re = re.compile(
        r"\*\*\* *END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*",
        re.IGNORECASE | re.DOTALL
    )

    start_match = start_re.search(text)
    start_idx = start_match.end() if start_match else (
        re.search(r"(?:^|\n)(chapter|i\.)\s+[A-Z0-9\.\- ]{2,}", text, re.IGNORECASE).start()
        if re.search(r"(?:^|\n)(chapter|i\.)\s+[A-Z0-9\.\- ]{2,}", text, re.IGNORECASE) else 0
    )

    end_match = end_re.search(text)
    end_idx = end_match.start() if end_match else (
        re.search(r"\*\*\* *END OF .{0,80}$", text, re.IGNORECASE | re.DOTALL).start()
        if re.search(r"\*\*\* *END OF .{0,80}$", text, re.IGNORECASE | re.DOTALL) else len(text)
    )

    return text[start_idx:end_idx].strip()


def save_text_to_file(text: str, path: str) -> None:
    """
    Save text to a file.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def fetch_and_clean(url: str, save_path: Optional[str] = None) -> Optional[str]:
    """
    Fetch text from URL, clean Gutenberg headers/footers, and optionally save to file.

    Args:
        url (str): URL to fetch text from.
        save_path (str, optional): Path to save cleaned text. If None, does not save.

    Returns:
        Optional[str]: Cleaned text or None if fetch failed.
    """
    raw_text = fetch_raw_text(url)
    if raw_text is None:
        return None

    cleaned_text = strip_gutenberg_header_footer(raw_text)

    if save_path:
        save_text_to_file(cleaned_text, save_path)

    return cleaned_text

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
