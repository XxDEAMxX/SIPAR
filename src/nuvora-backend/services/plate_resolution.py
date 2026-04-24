import re
from dataclasses import dataclass


LETTER_PATTERNS = ("LLLDDD", "LLLDDL")
MAX_CORRECTIONS_WITH_CONTEXT = 2
MAX_CORRECTIONS_WITHOUT_CONTEXT = 1

LETTER_TO_DIGIT = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "T": "7",
    "B": "8",
}

DIGIT_TO_LETTER = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "4": "A",
    "5": "S",
    "6": "G",
    "7": "T",
    "8": "B",
}

VALID_PLATE_REGEX = (
    re.compile(r"^[A-Z]{3}[0-9]{3}$"),
    re.compile(r"^[A-Z]{3}[0-9]{2}[A-Z]$"),
)


@dataclass(frozen=True)
class PlateCandidate:
    plate: str
    corrections: int
    pattern: str


@dataclass(frozen=True)
class PlateResolution:
    raw_plate: str
    resolved_plate: str | None
    corrections: int | None
    candidates: tuple[PlateCandidate, ...]
    reason: str | None = None


def sanitize_plate(raw_plate: str) -> str:
    return "".join(ch for ch in (raw_plate or "").upper() if ch.isalnum())


def is_valid_plate(plate: str) -> bool:
    return any(regex.match(plate) for regex in VALID_PLATE_REGEX)


def _convert_char(char: str, expected: str) -> tuple[str, int] | None:
    if expected == "L":
        if char.isalpha():
            return char, 0
        converted = DIGIT_TO_LETTER.get(char)
        if converted is None:
            return None
        return converted, 1

    if char.isdigit():
        return char, 0
    converted = LETTER_TO_DIGIT.get(char)
    if converted is None:
        return None
    return converted, 1


def build_plate_candidates(raw_plate: str) -> tuple[PlateCandidate, ...]:
    sanitized = sanitize_plate(raw_plate)
    if len(sanitized) != 6:
        return ()

    deduped: dict[str, PlateCandidate] = {}
    for pattern in LETTER_PATTERNS:
        resolved_chars: list[str] = []
        corrections = 0
        for char, expected in zip(sanitized, pattern, strict=True):
            converted = _convert_char(char, expected)
            if converted is None:
                break
            value, extra_corrections = converted
            resolved_chars.append(value)
            corrections += extra_corrections
        else:
            candidate_plate = "".join(resolved_chars)
            if not is_valid_plate(candidate_plate):
                continue
            current = deduped.get(candidate_plate)
            candidate = PlateCandidate(
                plate=candidate_plate,
                corrections=corrections,
                pattern=pattern,
            )
            if current is None or candidate.corrections < current.corrections:
                deduped[candidate_plate] = candidate

    return tuple(sorted(deduped.values(), key=lambda item: (item.corrections, item.plate)))


def resolve_plate(raw_plate: str, preferred_plates: list[str] | tuple[str, ...] = ()) -> PlateResolution:
    sanitized = sanitize_plate(raw_plate)
    candidates = build_plate_candidates(sanitized)
    if not candidates:
        return PlateResolution(
            raw_plate=sanitized,
            resolved_plate=None,
            corrections=None,
            candidates=(),
            reason="La lectura no coincide con un formato de placa válido.",
        )

    preferred_lookup = {plate.upper() for plate in preferred_plates}
    if preferred_lookup:
        matching_candidates = [
            candidate
            for candidate in candidates
            if candidate.plate in preferred_lookup and candidate.corrections <= MAX_CORRECTIONS_WITH_CONTEXT
        ]
        if matching_candidates:
            selected = min(matching_candidates, key=lambda item: (item.corrections, item.plate))
            return PlateResolution(
                raw_plate=sanitized,
                resolved_plate=selected.plate,
                corrections=selected.corrections,
                candidates=candidates,
            )

    standalone_candidates = [
        candidate for candidate in candidates if candidate.corrections <= MAX_CORRECTIONS_WITHOUT_CONTEXT
    ]
    if standalone_candidates:
        selected = min(standalone_candidates, key=lambda item: (item.corrections, item.plate))
        return PlateResolution(
            raw_plate=sanitized,
            resolved_plate=selected.plate,
            corrections=selected.corrections,
            candidates=candidates,
        )

    return PlateResolution(
        raw_plate=sanitized,
        resolved_plate=None,
        corrections=None,
        candidates=candidates,
        reason="La lectura requiere demasiadas correcciones para registrarse automáticamente.",
    )
