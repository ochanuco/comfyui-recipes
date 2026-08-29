# Script surface

`scripts/` is not the application layer. The only public application entry
point is:

```bash
uv run comfy-recipes --help
```

The Python package under `src/comfyui_recipes/` owns the generation workflows,
Yukari domain, external adapters, and CLI wiring. Files here are grouped by why
they still need to exist:

- `generate.py`, `yukari_recipe.py` — temporary compatibility facades. They
  contain no generation workflow; new callers use `comfy-recipes`.
- `queue_*.py`, `comfy_host.py`, `workflow_ui.py`,
  `refine_from_history.py` — low-level ComfyUI operator tools. They are useful
  for generic graph work, but are not the recorded Yukari generation path.
- `costume_check.py`, `palette_check.py`, `prompt_lint.py` — contract and
  request checks.
- `recolor_*.py`, `outline_stroke.py`, `line_*.py`, `stripe_paint.py`,
  `repin.py` — manual image utilities.
- `analysis/` — measurement and diagnostic CLIs.
- `archive/` — exhausted one-off experiments kept only as provenance.
- `*.sh`, `*.ps1` — environment setup and operator automation.

If a script starts coordinating a recorded batch, it belongs in
`application/` behind `comfy-recipes`; if it expresses Yukari policy, it
belongs in `domain/yukari/`.
