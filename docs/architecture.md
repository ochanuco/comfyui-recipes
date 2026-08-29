# Architecture

The repository uses four lightweight layers. This is a dependency rule, not a
full DDD framework.

```text
interfaces -> application -> domain
                    |            ^
                    v            |
              infrastructure ----+
```

## Domain

`src/comfyui_recipes/domain/` owns pure generation values and the Yukari
recipe: identity, costumes, poses, prompt edit order and delivery policy. It
does not parse CLI arguments, read environment variables or files, make HTTP
requests, open images, or know ComfyUI node ids.

`RenderSpec` is the boundary between the recipe and a graph adapter. The recipe
decides prompts, sampling parameters, sizes and filenames; the ComfyUI adapter
decides how those values are encoded as nodes and links.

## Application

`src/comfyui_recipes/application/` owns use cases: generate and record a batch,
finalize a selected generation, and manage its metadata. It coordinates domain
rules and concrete adapters without reimplementing either.

## Infrastructure

`src/comfyui_recipes/infrastructure/` owns ComfyUI graphs and HTTP, Chimera,
Discord, image processing and crash-resume persistence. External payload shapes
stay here.

## Interfaces

`src/comfyui_recipes/interfaces/` owns the single public `comfy-recipes` CLI.
Argument parsing stops at this boundary; commands call application use cases.

## Migration rule

The old modules under `scripts/` are temporary compatibility facades while the
application is moved. They may re-export the package but must not acquire new
domain or orchestration logic. The migration is complete when operational
shell scripts are the only maintained code left under `scripts/`.
