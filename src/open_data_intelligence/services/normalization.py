from __future__ import annotations

import re
import unicodedata

COMPANY_SUFFIXES = {
    "company",
    "corporation",
    "inc",
    "limited",
    "llc",
    "ltd",
    "тов",
    "пп",
}


def normalize_registration_code(value: str) -> str:
    return re.sub(r"[^A-ZА-ЯІЇЄҐ0-9]", "", value.upper())


def normalize_organization_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    tokens = re.findall(r"[\w]+", normalized, flags=re.UNICODE)
    meaningful = [token for token in tokens if token not in COMPANY_SUFFIXES]
    return " ".join(meaningful)
