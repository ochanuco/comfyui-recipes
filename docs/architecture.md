# Architecture

The repository uses four lightweight layers. This is a dependency rule, not a
full DDD framework.

```text
interfaces -> application -> domain
                    |            ^
                    v            |
              infrastructure ----+
```

The maintained application layout is:

```text
src/comfyui_recipes/
├── interfaces/          # argparse and dependency wiring
├── application/         # generate, finalize and metadata workflows
├── domain/
│   ├── generation/      # shared values and prompt checks
│   └── yukari/          # profile, costumes, poses and recipe policy
└── infrastructure/
    ├── chimera/         # Management API
    ├── comfyui/         # HTTP client and graph encoders
    ├── imaging/         # delivery post-processing
    ├── notifications/   # Discord side channel
    └── persistence/     # crash-resume state
comfy_nodes/
└── yukari_finalize/      # ComfyUI custom node pack wrapping imaging/ for the finalize graph
```

`infrastructure/imaging/` is shared: `comfy_nodes/yukari_finalize/` wraps its
functions unchanged as ComfyUI nodes rather than duplicating them.

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

`comfy-recipes` is the only public application entry point. The old
`scripts/generate.py` and `scripts/yukari_recipe.py` modules are temporary
compatibility facades and must not acquire new domain or orchestration logic.
Other files under `scripts/` are operator or research utilities, not alternate
application entry points; they are being grouped separately as the migration
continues.
