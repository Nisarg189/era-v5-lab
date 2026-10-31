"""Text normalize for decontamination. The same function runs on benchmark items and on documents.

A fingerprint set records the ID of its normalizer in MANIFEST.json. fpset.py reads that ID and
uses the same normalizer to check documents, so a set is always read the way it was built.

    g9-v1    fingerprints v1. Words, NFKC, lower().
    spec-v1  fingerprints v2. The spec v1 normalize function of Team 1, then the g9-v1 steps.
             Training text goes through spec v1, so benchmark text must go through it too.
"""

import re
import sys
import unicodedata

DEFAULT_ID = "g9-v1"


def _mark_ranges():
    # Python \w does not match combining marks (Unicode M*), so Indic vowel signs
    # would split words. Add all M* characters to the word class.
    ranges, start, prev = [], None, None
    for cp in range(sys.maxunicode + 1):
        if unicodedata.category(chr(cp))[0] == "M":
            if start is None:
                start = cp
            prev = cp
        elif start is not None:
            ranges.append((start, prev))
            start = None
    if start is not None:
        ranges.append((start, prev))
    return "".join(f"\\U{a:08x}-\\U{b:08x}" for a, b in ranges)


# A word is a run of Unicode letters (L*), marks (M*) and numbers (N*).
# Everything else (spaces, punctuation, symbols, underscore) separates words.
WORD_RE = re.compile(f"(?:[^\\W_]|[{_mark_ranges()}])+")


def _split(text):
    """The g9-v1 steps: [(word, char_offset)]. Offsets point into the given text."""
    out = []
    for m in WORD_RE.finditer(text):
        tok = unicodedata.normalize("NFKC", m.group()).lower()
        # NFKC can add separators (for example "½" -> "1⁄2"), so split again.
        for w in WORD_RE.findall(tok):
            out.append((w, m.start()))
    return out


class NormalizerNotReady(ValueError):
    pass


class Normalizer:
    """One normalize ID. prepare: a text -> text function that runs before the g9-v1 steps."""

    def __init__(self, normalize_id, description, prepare=None, missing=None):
        self.id = normalize_id
        self.description = description
        self.prepare = prepare
        self.missing = missing  # why the normalizer cannot run yet, or None

    def words_with_offsets(self, text):
        """Return [(word, char_offset)] for text."""
        if self.missing:
            raise NormalizerNotReady(f"normalize {self.id}: {self.missing}")
        if self.prepare:
            text = self.prepare(text)
        return _split(text)

    def normalize(self, text):
        """Text -> list of normalized words."""
        return [w for w, _ in self.words_with_offsets(text)]


NORMALIZERS = {
    "g9-v1": Normalizer(
        "g9-v1",
        "words = runs of Unicode L/M/N characters; each word NFKC then lower(); everything else separates words"),
    "spec-v1": Normalizer(
        "spec-v1",
        "spec v1 normalize function of Team 1, then the g9-v1 steps",
        missing="the spec v1 normalize function of Team 1 is not added yet"),
}


def get(normalize_id):
    """The normalizer for an ID. Unknown IDs and normalizers that cannot run yet are refused."""
    if normalize_id not in NORMALIZERS:
        raise ValueError(f"unknown normalize_id {normalize_id!r}, known: {sorted(NORMALIZERS)}")
    norm = NORMALIZERS[normalize_id]
    if norm.missing:
        raise NormalizerNotReady(f"normalize {normalize_id}: {norm.missing}")
    return norm


# The g9-v1 functions, for code that does not read a fingerprint set.
NORMALIZE_ID = DEFAULT_ID
DESCRIPTION = NORMALIZERS[DEFAULT_ID].description
words_with_offsets = NORMALIZERS[DEFAULT_ID].words_with_offsets
normalize = NORMALIZERS[DEFAULT_ID].normalize
