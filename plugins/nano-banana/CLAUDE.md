# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nano Banana is a Claude Code plugin/skill for generating images with Google's Nano Banana models. The whole family lives in this one skill:

| Model | `--model` | ID | Aspect ratios | Sizes |
|-------|-----------|----|---------------|-------|
| Nano Banana 2 (default) | `nano-banana-2` / `2` | `gemini-3.1-flash-image` | 14 | 512, 1K, 2K, 4K |
| Nano Banana 2 Lite | `nano-banana-2-lite` / `2-lite` | `gemini-3.1-flash-lite-image` | 14 | 1K |
| Nano Banana Pro | `nano-banana-pro` / `pro` | `gemini-3-pro-image` | 10 | 1K, 2K, 4K |
| Nano Banana (legacy) | `nano-banana` / `flash` | `gemini-2.5-flash-image` | 10 | fixed ~1024px |

The 14-ratio set is the 10 shared ones (`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`) plus the four the Gemini 3.1 image models added: `1:4`, `4:1`, `1:8`, `8:1`.

It integrates as a skill that can be invoked via `/generate` or triggered by image generation requests.

## Running the Image Generation Script

```bash
uv run skills/generate/scripts/image.py \
  --prompt "Your image description" \
  --output "/path/to/output"
```

The extension on `--output` is replaced with whatever format the model returns (the Gemini 3 models typically return JPEG, the legacy model typically returns PNG). The final path is printed on stdout.

Options:
- `--prompt` (required): Image description
- `--output` (required): Output file path. Extension is replaced with the format the model returns.
- `--aspect` (optional): Named shortcut (`square`, `landscape`, `portrait`, `ultrawide`, `banner`, `skyscraper`) or direct ratio (e.g. `4:3`, `16:9`, `21:9`, `8:1`). Default: square
- `--reference` (optional, repeatable): Path to reference image for style guidance. Use multiple times for multiple references.
- `--model` (optional): `nano-banana-2` (default), `nano-banana-2-lite`, `nano-banana-pro`, `nano-banana`. Aliases `2`, `2-lite`, `pro`, `flash` still work.
- `--size` (optional): `512` (Nano Banana 2 only), `1K` (default), `2K`, `4K` (Nano Banana 2 and Pro). Ignored by the legacy model.
- `--thinking` (optional): `minimal` or `high`, Nano Banana 2 and 2 Lite only.

## Prerequisites

- `GEMINI_API_KEY` environment variable must be set with a Google AI API key
- Python 3.10+ with `uv` package manager
- Dependencies (`google-genai`, `pillow`) are managed via inline script metadata

## Architecture

```
nano-banana/
├── skills/
│   └── generate/
│       ├── SKILL.md          # Skill definition and usage docs
│       └── scripts/
│           └── image.py      # Main image generation script
└── .claude/
    └── settings.local.json   # Claude Code permission settings
```

The plugin follows Claude Code's skill structure where `SKILL.md` defines the skill metadata (name, description, triggers) and provides usage instructions. The Python script uses Google's GenAI SDK with inline PEP 723 dependencies for zero-config execution via `uv run`.
