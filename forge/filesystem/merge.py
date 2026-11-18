"""Fusion textuelle a trois voies, sans dependance externe.

La fonction ne devine jamais une resolution : des modifications qui se
chevauchent sont retournees comme conflit et restent soumises a la fusion
manuelle existante.
"""
from dataclasses import dataclass
import difflib


@dataclass(frozen=True)
class MergeResult:
    content: str | None
    conflicts: tuple[dict, ...]

    @property
    def clean(self):
        return self.content is not None and not self.conflicts


def _changes(base, variant):
    matcher = difflib.SequenceMatcher(a=base, b=variant, autojunk=False)
    return [(i1, i2, variant[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"]


def _overlap(left, right):
    a1, a2, _ = left
    b1, b2, _ = right
    if a1 == a2 and b1 == b2:
        return a1 == b1
    if a1 == a2:
        return b1 <= a1 <= b2
    if b1 == b2:
        return a1 <= b1 <= a2
    return max(a1, b1) < min(a2, b2)


def three_way_merge(base_text, current_text, generated_text):
    """Fusionne current et generated relativement a base, ou decrit les conflits."""
    if current_text == generated_text:
        return MergeResult(current_text, ())
    if current_text == base_text:
        return MergeResult(generated_text, ())
    if generated_text == base_text:
        return MergeResult(current_text, ())
    base = base_text.splitlines(keepends=True)
    current = current_text.splitlines(keepends=True)
    generated = generated_text.splitlines(keepends=True)
    local_changes = _changes(base, current)
    generated_changes = _changes(base, generated)
    conflicts = []
    for local in local_changes:
        for remote in generated_changes:
            if _overlap(local, remote) and local != remote:
                conflicts.append({"base_start": min(local[0], remote[0]) + 1,
                                  "base_end": max(local[1], remote[1]),
                                  "current": "".join(local[2]),
                                  "generated": "".join(remote[2])})
    if conflicts:
        return MergeResult(None, tuple(conflicts))
    merged = list(base)
    for start, end, replacement in sorted(local_changes + generated_changes, key=lambda item: item[0], reverse=True):
        merged[start:end] = replacement
    return MergeResult("".join(merged), ())
