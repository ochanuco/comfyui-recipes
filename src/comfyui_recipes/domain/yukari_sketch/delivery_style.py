"""Yukari-sketch's delivery policy: what the finalize redraw runs at."""

from __future__ import annotations

FINALIZE_SIZE = 2560
# Longest side the delivered file is downscaled to after the redraw.
DELIVER_SIZE = 1536
# 0.8 re-draws the line, but on a full-body base it also re-decides the held
# props and the expression (a paper cup became a sheet of paper); 0.55 keeps
# them and still turns the latent route's staircase into stroke.
FINALIZE_DENOISE = 0.55
# A layerdiffuse raw already holds its own scene at full opacity; a stronger
# redraw invents background objects it never drew (a chair behind the
# figure) and washes the delivery bands out.
FINALIZE_DENOISE_LAYERDIFFUSE = 0.55
FINALIZE_SAMPLER = ("euler", "normal")
# The latent route leaves a staircase on hard contours that the redraw turns
# into visible stroke -- the sketch look this recipe delivers for.
FINALIZE_LATENT_ROUTE = True
# Deliverables are cutouts; the flat-backdrop composite's binary edge aliases.
FINALIZE_TRANSPARENT = True
