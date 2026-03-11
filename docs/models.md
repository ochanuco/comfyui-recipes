# Model Storage Notes

The bootstrap scripts create `.local/assets` as the default model root rendered into `extra_model_paths.yaml`.

Suggested layout:

- `.local/assets/checkpoints`
- `.local/assets/loras`
- `.local/assets/controlnet`
- `.local/assets/vae`
- `.local/assets/upscale_models`

If you already keep models elsewhere, update `config/extra_model_paths.yaml.tmpl` and rerun `./scripts/update-comfyui.sh`.
