"""Yukari-sketch's delivery policy: what the finalize redraw runs at."""

from __future__ import annotations

FINALIZE_SIZE = 2560
FINALIZE_DENOISE = 0.55
FINALIZE_SAMPLER = ("euler", "normal")
# The latent route leaves a staircase on hard contours that the redraw turns
# into visible stroke -- the sketch look this recipe delivers for.
FINALIZE_LATENT_ROUTE = True
