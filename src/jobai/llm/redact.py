"""Replace personal data with placeholders before a call; restore afterwards."""

import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


@dataclass
class Redactor:
    name: str = field(default="", repr=False)
    email: str = field(default="", repr=False)
    phone: str = field(default="", repr=False)
    address: str = field(default="", repr=False)
    mapping: dict[str, str] = field(default_factory=dict, repr=False)

    def __repr__(self) -> str:
        return f"Redactor(placeholders={len(self.mapping)})"

    __str__ = __repr__

    def redact(self, text: str) -> str:
        for label, value in (
            ("ADDRESS", self.address),
            ("EMAIL", self.email),
            ("PHONE", self.phone),
            ("NAME", self.name),
        ):
            value = value.strip()
            if value:
                ph = f"[[{label}]]"
                text, n = re.subn(re.escape(value), ph, text, flags=re.IGNORECASE)
                if n:
                    self.mapping[ph] = value
        text = EMAIL_RE.sub(lambda m: self._extra("EMAIL", m.group(0)), text)
        return PHONE_RE.sub(lambda m: self._extra("PHONE", m.group(0)), text)

    def _extra(self, label: str, original: str) -> str:
        for ph, orig in self.mapping.items():
            if orig == original:
                return ph
        ph = f"[[{label}_{len(self.mapping) + 1}]]"
        self.mapping[ph] = original
        return ph

    def restore(self, text: str) -> str:
        for ph, orig in self.mapping.items():
            text = text.replace(ph, orig)
        return text
