#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai",
#     "pillow",
# ]
# ///
"""
Generate images using Google's Gemini image models (the Nano Banana family).

Usage:
    uv run image.py --prompt "A colorful abstract pattern" --output "./hero.png"
    uv run image.py --prompt "Minimalist icon" --output "./icon.png" --aspect landscape
    uv run image.py --prompt "Similar style image" --output "./new.png" --reference "./existing.png"
    uv run image.py --prompt "Blend these styles" --output "./new.png" --reference "./a.png" --reference "./b.png"
    uv run image.py --prompt "High quality art" --output "./art.png" --model pro --size 2K
    uv run image.py --prompt "Fast high-res" --output "./fast" --model 2 --size 4K --aspect 8:1
    uv run image.py --prompt "Cheap and quick" --output "./draft" --model 2-lite

The output file's extension is set automatically from the format the model returns
(e.g. .jpg or .png), so any extension you pass on --output will be replaced.
"""

import argparse
import mimetypes
import os
import sys

from google import genai
from google.genai import types
from PIL import Image

MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

# Aspect ratios shared by every Nano Banana model
BASE_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
]

# Extra ratios introduced by the Gemini 3.1 image models (Nano Banana 2 family)
EXTENDED_ASPECT_RATIOS = ["1:4", "4:1", "1:8", "8:1"]

# Full set (14 ratios) supported by Nano Banana 2 and Nano Banana 2 Lite
ALL_ASPECT_RATIOS = BASE_ASPECT_RATIOS + EXTENDED_ASPECT_RATIOS

# One entry per Nano Banana model. The key is what --model accepts.
MODELS = {
    "nano-banana": {
        "id": "gemini-2.5-flash-image",
        "label": "Nano Banana (legacy)",
        "aspect_ratios": BASE_ASPECT_RATIOS,
        "sizes": [],            # no image_size control, always ~1024px
        "image_config": False,  # aspect ratio is steered through the prompt only
        "thinking": False,
    },
    "nano-banana-pro": {
        "id": "gemini-3-pro-image",
        "label": "Nano Banana Pro",
        "aspect_ratios": BASE_ASPECT_RATIOS,
        "sizes": ["1K", "2K", "4K"],
        "image_config": True,
        "thinking": False,      # always thinks, level not configurable
    },
    "nano-banana-2": {
        "id": "gemini-3.1-flash-image",
        "label": "Nano Banana 2",
        "aspect_ratios": ALL_ASPECT_RATIOS,
        "sizes": ["0.5K", "1K", "2K", "4K"],
        "image_config": True,
        "thinking": True,
    },
    "nano-banana-2-lite": {
        "id": "gemini-3.1-flash-lite-image",
        "label": "Nano Banana 2 Lite",
        "aspect_ratios": ALL_ASPECT_RATIOS,
        "sizes": ["1K"],
        "image_config": True,
        "thinking": True,
    },
}

# Short names for --model, including the ones earlier versions of this skill used
MODEL_ALIASES = {
    "flash": "nano-banana",
    "2.5": "nano-banana",
    "pro": "nano-banana-pro",
    "3-pro": "nano-banana-pro",
    "2": "nano-banana-2",
    "3.1": "nano-banana-2",
    "lite": "nano-banana-2-lite",
    "2-lite": "nano-banana-2-lite",
    "3.1-lite": "nano-banana-2-lite",
}

MODEL_CHOICES = list(MODELS.keys()) + list(MODEL_ALIASES.keys())

# Named shortcuts for common aspect ratios
ASPECT_ALIASES = {
    "square": "1:1",
    "landscape": "16:9",
    "portrait": "9:16",
    "ultrawide": "21:9",
    "banner": "4:1",
    "skyscraper": "1:4",
}

# --size accepts these spellings; the value on the right is what we ask the API for
SIZE_ALIASES = {
    "512": "0.5K",
    "512px": "0.5K",
    "0.5k": "0.5K",
    "1k": "1K",
    "2k": "2K",
    "4k": "4K",
}

SIZE_CHOICES = ["512", "512px", "0.5K", "1K", "2K", "4K"]

# The API has used more than one spelling for the 512px tier; try them in order.
SIZE_FALLBACKS = {"0.5K": ["0.5K", "512px", "512"]}

ASPECT_DESCRIPTIONS = {
    "1:1": "Generate a square image (1:1 aspect ratio).",
    "1:4": "Generate a tall narrow image (1:4 aspect ratio).",
    "1:8": "Generate a very tall narrow image (1:8 aspect ratio).",
    "2:3": "Generate a tall image (2:3 aspect ratio).",
    "3:2": "Generate a wide image (3:2 aspect ratio).",
    "3:4": "Generate a tall image (3:4 aspect ratio).",
    "4:1": "Generate a wide panoramic image (4:1 aspect ratio).",
    "4:3": "Generate a landscape image (4:3 aspect ratio).",
    "4:5": "Generate a slightly tall image (4:5 aspect ratio).",
    "5:4": "Generate a slightly wide image (5:4 aspect ratio).",
    "8:1": "Generate a very wide panoramic image (8:1 aspect ratio).",
    "9:16": "Generate a portrait/tall image (9:16 aspect ratio).",
    "16:9": "Generate a landscape/wide image (16:9 aspect ratio).",
    "21:9": "Generate an ultrawide image (21:9 aspect ratio).",
}


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def resolve_model(model: str) -> tuple[str, dict]:
    """Resolve a --model value (canonical name or alias) to its spec."""
    key = MODEL_ALIASES.get(model, model)
    if key not in MODELS:
        fail(f"Unknown model '{model}'. Valid values: {', '.join(MODEL_CHOICES)}")
    return key, MODELS[key]


def resolve_aspect(aspect: str) -> str:
    """Resolve a named alias or direct ratio string to a ratio string."""
    return ASPECT_ALIASES.get(aspect, aspect)


def resolve_size(size: str) -> str:
    """Normalize a --size value to the spelling the API expects."""
    if size in SIZE_ALIASES:
        return SIZE_ALIASES[size]
    return SIZE_ALIASES.get(size.lower(), size)


def get_aspect_instruction(aspect_ratio: str) -> str:
    """Return aspect ratio instruction for the prompt."""
    return ASPECT_DESCRIPTIONS.get(
        aspect_ratio, f"Generate an image with {aspect_ratio} aspect ratio."
    )


def build_thinking_config(level: str):
    """Build a ThinkingConfig for the Gemini 3.1 image models."""
    try:
        return types.ThinkingConfig(thinking_level=level)
    except Exception as exc:  # older SDK without thinking_level
        fail(
            f"This google-genai version does not support --thinking ({exc}). "
            "Upgrade the SDK or drop the flag."
        )


def is_bad_image_size(exc: Exception) -> bool:
    """True only when the API rejected the request because of image_size."""
    text = str(exc).lower()
    if "invalid_argument" not in text and "invalid argument" not in text:
        return False
    return "image_size" in text or "imagesize" in text or "image size" in text


def call_model(client, spec, contents, aspect_ratio, size_value, thinking):
    """Send the request, retrying alternate spellings of the 512px size tier."""
    model_id = spec["id"]

    if not spec["image_config"]:
        # Legacy Nano Banana: aspect ratio rides along in the prompt
        return client.models.generate_content(model=model_id, contents=contents)

    candidates = SIZE_FALLBACKS.get(size_value, [size_value])
    last_error = None

    for index, candidate in enumerate(candidates):
        config_args = {
            "response_modalities": ["TEXT", "IMAGE"],
            "image_config": types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=candidate,
            ),
        }
        if thinking:
            config_args["thinking_config"] = build_thinking_config(thinking)

        try:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(**config_args),
            )
        except Exception as exc:
            last_error = exc
            if index == len(candidates) - 1 or not is_bad_image_size(exc):
                raise
            print(
                f"Note: image_size '{candidate}' rejected, retrying as "
                f"'{candidates[index + 1]}'.",
                file=sys.stderr,
            )

    raise last_error


def generate_image(
    prompt: str,
    output_path: str,
    aspect: str = "square",
    references: list[str] | None = None,
    model: str = "nano-banana-2",
    size: str = "1K",
    thinking: str | None = None,
) -> None:
    """Generate an image using Gemini and save to output_path."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        fail("GEMINI_API_KEY environment variable not set")

    model_key, spec = resolve_model(model)
    client = genai.Client(api_key=api_key)

    aspect_ratio = resolve_aspect(aspect)
    if aspect_ratio not in spec["aspect_ratios"]:
        fail(
            f"Aspect ratio '{aspect_ratio}' not supported for model '{model_key}' "
            f"({spec['label']}). Valid ratios: {', '.join(spec['aspect_ratios'])}"
        )

    size_value = resolve_size(size)
    if spec["sizes"]:
        if size_value not in spec["sizes"]:
            fail(
                f"Size '{size}' not supported for model '{model_key}' ({spec['label']}). "
                f"Valid sizes: {', '.join(spec['sizes'])}"
            )
    elif size_value != "1K":
        print(
            f"Note: {spec['label']} has no image size control; --size {size} is ignored.",
            file=sys.stderr,
        )

    if thinking and not spec["thinking"]:
        print(
            "Note: --thinking is only configurable on the Nano Banana 2 models; "
            f"ignored for {spec['label']}.",
            file=sys.stderr,
        )
        thinking = None

    aspect_instruction = get_aspect_instruction(aspect_ratio)
    full_prompt = f"{aspect_instruction} {prompt}"

    # Build contents with optional reference images
    contents: list = []
    if references:
        for ref_path in references:
            if not os.path.exists(ref_path):
                fail(f"Reference image not found: {ref_path}")
            contents.append(Image.open(ref_path))
        if len(references) == 1:
            full_prompt = f"{full_prompt} Use the provided image as a reference for style, composition, or content."
        else:
            full_prompt = f"{full_prompt} Use the provided {len(references)} images as references for style, composition, or content."
    contents.append(full_prompt)

    try:
        response = call_model(client, spec, contents, aspect_ratio, size_value, thinking)
    except Exception as exc:
        fail(f"{spec['label']} ({spec['id']}) request failed: {exc}")

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Extract image from response
    for part in response.parts:
        if part.text is not None:
            print(f"Model response: {part.text}")
        elif part.inline_data is not None:
            mime_type = part.inline_data.mime_type or "image/png"
            ext = MIME_EXTENSIONS.get(mime_type) or mimetypes.guess_extension(mime_type) or ".bin"
            base, _ = os.path.splitext(output_path)
            final_path = base + ext
            with open(final_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"Image saved to: {final_path}")
            return

    fail("No image data in response")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with the Nano Banana models (Gemini image generation)"
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Description of the image to generate",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path. The extension is set automatically from the format the model returns (e.g. .jpg or .png).",
    )
    parser.add_argument(
        "--aspect",
        choices=list(ASPECT_ALIASES.keys()) + ALL_ASPECT_RATIOS,
        default="square",
        help="Aspect ratio: named shortcut (square, landscape, portrait, ultrawide, banner, skyscraper) or direct ratio (e.g. 4:3, 21:9, 8:1). Default: square",
    )
    parser.add_argument(
        "--reference",
        action="append",
        dest="references",
        help="Path to a reference image (can be specified multiple times for multiple references)",
    )
    parser.add_argument(
        "--model",
        choices=MODEL_CHOICES,
        default="nano-banana-2",
        help=(
            "Model: nano-banana (legacy, 1024px), nano-banana-pro (up to 4K), "
            "nano-banana-2 (default, fast + up to 4K, 14 aspect ratios), "
            "nano-banana-2-lite (cheapest, 1K). Short aliases: flash, pro, 2, 2-lite."
        ),
    )
    parser.add_argument(
        "--size",
        choices=SIZE_CHOICES,
        default="1K",
        help="Image resolution: 512 (nano-banana-2 only), 1K (default), 2K, 4K (nano-banana-2 and pro). Ignored by the legacy model.",
    )
    parser.add_argument(
        "--thinking",
        choices=["minimal", "high"],
        default=None,
        help="Thinking level for the Nano Banana 2 models. Default: model default (minimal).",
    )

    args = parser.parse_args()
    generate_image(
        args.prompt,
        args.output,
        args.aspect,
        args.references,
        args.model,
        args.size,
        args.thinking,
    )


if __name__ == "__main__":
    main()
