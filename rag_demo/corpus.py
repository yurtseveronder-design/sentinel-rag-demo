from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str


def load(directory):
    """One chunk per paragraph; headings are skipped."""
    chunks = []
    for path in sorted(Path(directory).glob("*.md")):
        for block in path.read_text(encoding="utf-8").split("\n\n"):
            block = block.strip()
            if block and not block.startswith("#"):
                chunks.append(Chunk(path.name, block))
    return chunks
