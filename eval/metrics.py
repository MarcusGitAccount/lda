"""Precision, recall and F-scores.

A missed name is a leak. A false hit only makes the text harder to read. So recall is the
number that decides, and F2 (which counts recall twice as much as precision) is the score that
we track next to it. We also report F1, because the papers use it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counts:
    tp: int = 0  # gold items that the tool hides
    fp: int = 0  # hidden items that are not gold
    fn: int = 0  # gold items that the tool misses (leaks)

    def add(self, other: Counts) -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    def f(self, beta: float = 1.0) -> float:
        p, r = self.precision, self.recall
        if p == 0 and r == 0:
            return 0.0
        return (1 + beta**2) * p * r / (beta**2 * p + r)

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f(1), 4),
            "f2": round(self.f(2), 4),
        }
