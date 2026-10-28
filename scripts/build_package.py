"""Rebuild combined prose and checksums after editing the source documents."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
FILES = ['README.md', '01-REQUIREMENTS.md', '02-HLD.md', '03-LLD.md',
         '04-TECHNOLOGY-AND-SOURCES.md', '05-IMPLEMENTATION-PLAN.md',
         '06-ACCEPTANCE-AND-EVALS.md', '07-NEXT-CHAT-PROMPT.md']
parts = ['# Complete design handoff\n\nVersion 1.0 — 28 October 2026. This combines the prose specification for another chat. Separate files remain authoritative for navigation; contracts and synthetic examples accompany the repository/ZIP. This is a design, not a running platform.\n']
for filename in FILES:
    text = (ROOT / filename).read_text()
    if filename == 'README.md':
        text = text.replace('| [Combined design](MASTER-DESIGN.md) | The prose documents in one file for uploading into another chat |\n', '')
    parts.append('\n---\n\nSource document: ' + filename + '\n\n' + text)
(ROOT / 'MASTER-DESIGN.md').write_text('\n'.join(parts))
checksums = []
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or path.name == 'checksums.sha256':
        continue
    rel = path.relative_to(ROOT)
    if any(part.startswith('.') or part == '__pycache__' for part in rel.parts):
        continue
    checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + rel.as_posix())
(ROOT / 'checksums.sha256').write_text('\n'.join(checksums) + '\n')
print(f'Built combined design and checksums for {len(checksums)} files.')
