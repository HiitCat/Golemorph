"""Frequency-aware sampling of name entries.

The frequency column is the drawing weight: a uniform shuffle would hand out
`Wang` exactly as often as `Nu`, which is not what a realistic campaign
looks like.
"""

from __future__ import annotations

import itertools
import random
from bisect import bisect_right

from .models import NameEntry


class NameSampler:
    """Draws entries with probability proportional to their real frequency."""

    def __init__(self, entries, *, weighted: bool = True) -> None:
        self._entries = tuple(entries)
        if not self._entries:
            raise ValueError("no entries to sample from")
        self._weighted = weighted
        self._weights = (
            [e.frequency for e in self._entries]
            if weighted
            else [1] * len(self._entries)
        )
        self._cumulative = list(itertools.accumulate(self._weights))

    def sample(self, rng: random.Random) -> NameEntry:
        """One draw, weighted by frequency (or uniform when not weighted)."""
        pick = rng.uniform(0, self._cumulative[-1])
        return self._entries[bisect_right(self._cumulative, pick)]

    def sample_many(self, rng: random.Random, k: int) -> list[NameEntry]:
        """Draw `k` names, weighted by frequency.

        Within the pool size this is Efraimidis-Spirakis key sampling (keep the
        top `k` keys of `u ** (1/w)`): a size-biased set of *distinct*
        names, so a batch of personas stays varied yet realistic. Beyond the
        pool size, independent draws repeat names rather than fail, so
        `-n 500` on a 500-row dataset still works.
        """
        if k > len(self._entries):
            return [self.sample(rng) for _ in range(k)]
        keys = [
            (rng.random() ** (1.0 / weight), entry)
            for weight, entry in zip(self._weights, self._entries)
        ]
        keys.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in keys[:k]]

