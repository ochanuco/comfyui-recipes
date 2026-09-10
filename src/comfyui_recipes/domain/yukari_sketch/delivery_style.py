"""Yukari-sketch's delivery policy: what the finalize redraw runs at."""

from __future__ import annotations

FINALIZE_SIZE = 2560
# Longest side the delivered file is downscaled to after the redraw.
DELIVER_SIZE = 1536
# Under ~0.7 the redraw keeps the base pass's own rough line instead of
# re-drawing it, and the delivery reads as scribble rather than sketch.
FINALIZE_DENOISE = 0.8
# A layerdiffuse raw's own alpha already holds its scene at full opacity;
# above ~0.6 the redraw invents background objects the raw never drew (a
# chair behind the figure) and washes the delivery bands out.
FINALIZE_DENOISE_LAYERDIFFUSE = 0.55
FINALIZE_SAMPLER = ("euler", "normal")
# The latent route leaves a staircase on hard contours that the redraw turns
# into visible stroke -- the sketch look this recipe delivers for.
FINALIZE_LATENT_ROUTE = True
# Deliverables are cutouts; the flat-backdrop composite's binary edge aliases.
FINALIZE_TRANSPARENT = True
