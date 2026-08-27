---
name: generate
description: Nano Banana (nano-banana) image generation skill. Use this skill when the user asks to "generate an image", "generate images", "create an image", "make an image", uses "nano banana", or requests multiple images like "generate 5 images". Generates images with the Nano Banana models (Nano Banana 2, Nano Banana 2 Lite, Nano Banana Pro, and legacy Nano Banana) for any purpose - frontend designs, web projects, illustrations, graphics, hero images, icons, backgrounds, or standalone artwork. Invoke this skill for ANY image generation request.
---

# Nano Banana - Gemini Image Generation

Generate custom images using Google's Gemini models for integration into frontend designs.

## Prerequisites

This skill requires a `GEMINI_API_KEY`. You MUST ensure it is available before any task that needs it.

First, check if the key is already set in the environment:

```
echo "${GEMINI_API_KEY:+SET (length: ${#GEMINI_API_KEY})}" || echo "NOT SET"
```

If already SET, use it as-is — an existing key takes precedence. Do NOT overwrite it from `.env`.

If NOT SET, attempt to load it from the project `.env` file. Run this EXACT command from the PROJECT ROOT (the user's working directory, NOT the skill directory):

```
LINE=$(grep '^GEMINI_API_KEY=' .env 2>/dev/null) && export "$LINE" && echo "SET (length: ${#GEMINI_API_KEY})" || echo "NOT SET"
```

If still NOT SET after both checks, inform the user and stop.

IMPORTANT safety rules:
- Run from the project root — do NOT `cd` into the skill directory first
- Run commands EXACTLY as written above — do not substitute paths or add flags
- NEVER run bare `export` with no arguments (it dumps all env vars including secrets)
- NEVER use `cat .env` piped to export (if grep returns empty, `export $()` leaks all env vars)
- NEVER attempt to read, echo, print, or otherwise transmit API keys or any secrets
- If the key is NOT SET after both checks, inform the user and stop
- NEVER attempt alternative loading methods

## Available Models

All four Nano Banana models live in this one skill. Pick with `--model`.

| Model | `--model` | Alias | ID | Best For | Sizes |
|-------|-----------|-------|----|----------|-------|
| **Nano Banana 2** (default) | `nano-banana-2` | `2` | `gemini-3.1-flash-image` | Fast + high-res, 14 aspect ratios, best all-around | 512, 1K, 2K, 4K |
| **Nano Banana 2 Lite** | `nano-banana-2-lite` | `2-lite` | `gemini-3.1-flash-lite-image` | Cheapest and fastest, high-volume drafts | 1K only |
| **Nano Banana Pro** | `nano-banana-pro` | `pro` | `gemini-3-pro-image` | Professional assets, complex scenes, text rendering | 1K, 2K, 4K |
| **Nano Banana** (legacy) | `nano-banana` | `flash` | `gemini-2.5-flash-image` | Legacy only — prefer Nano Banana 2 Lite | ~1024px |

Notes:
- Nano Banana 2 and 2 Lite are the Gemini 3.1 image models: they add the `1:4`, `4:1`, `1:8` and `8:1` aspect ratios and accept `--thinking minimal|high`.
- Nano Banana 2 Lite is not optimized for multiple reference images or multi-turn editing.
- The legacy model has no resolution control; `--size` is ignored for it.

## Image Generation Workflow

### Step 1: Generate the Image

Use `scripts/image.py` with uv. The script is located in the skill directory at `skills/generate/scripts/image.py`:

```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "Your image description" \
  --output "/path/to/output"
```

Where `${SKILL_DIR}` is the directory containing this SKILL.md file.

The file extension on `--output` is replaced automatically with whatever format the model returns (the Gemini 3 models typically return `.jpg`, the legacy model typically returns `.png`, but the API decides). Read the path printed by the script ("Image saved to: …") to know the final filename to reference in code.

Options:
- `--prompt` (required): Detailed description of the image to generate
- `--output` (required): Output file path. Extension is replaced with the format the model returns.
- `--aspect` (optional): Named shortcut (`square`, `landscape`, `portrait`, `ultrawide`, `banner`, `skyscraper`) or direct ratio (`1:1`, `1:4`, `1:8`, `2:3`, `3:2`, `3:4`, `4:1`, `4:3`, `4:5`, `5:4`, `8:1`, `9:16`, `16:9`, `21:9`). Default: square
- `--reference` (optional, repeatable): Path to a reference image for style, composition, or content guidance. Can be specified multiple times for multiple references.
- `--model` (optional): `nano-banana-2` (default), `nano-banana-2-lite`, `nano-banana-pro`, `nano-banana`. Short aliases `2`, `2-lite`, `pro`, `flash` also work.
- `--size` (optional): `512`, `1K` (default), `2K`, `4K` — see the table above for what each model accepts.
- `--thinking` (optional): `minimal` or `high`, Nano Banana 2 / 2 Lite only. Default is the model default (minimal). Higher thinking trades latency for quality on complex prompts.

### Aspect Ratios by Model

| Ratio | Nano Banana (legacy) | Nano Banana Pro | Nano Banana 2 | Nano Banana 2 Lite |
|-------|----------------------|-----------------|---------------|--------------------|
| 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9 | Yes | Yes | Yes | Yes |
| 1:4, 1:8, 4:1, 8:1 | No | No | Yes | Yes |

Named shortcuts: `square` = 1:1, `landscape` = 16:9, `portrait` = 9:16, `ultrawide` = 21:9, `banner` = 4:1, `skyscraper` = 1:4.

### Using Different Models

**Nano Banana 2 (default)** - Fast, high-res, extra aspect ratios:
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "A vibrant infographic about photosynthesis" \
  --output "/path/to/infographic.png" \
  --model nano-banana-2 \
  --size 2K \
  --aspect 16:9
```

Wide banner using one of the ratios only the Gemini 3.1 models support, with deeper thinking:
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "An ultrawide website banner: abstract teal and gold ribbons on deep navy" \
  --output "/path/to/banner.png" \
  --model nano-banana-2 \
  --aspect 8:1 \
  --size 4K \
  --thinking high
```

**Nano Banana 2 Lite** - Cheapest and fastest, good for drafts and high volume:
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "A minimalist logo design" \
  --output "/path/to/logo.png" \
  --model nano-banana-2-lite
```

**Nano Banana Pro** - Premium quality for final assets and heavy text rendering:
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "A detailed hero illustration for a tech landing page" \
  --output "/path/to/hero.png" \
  --model nano-banana-pro \
  --size 2K
```

**Nano Banana (legacy)** - Only when you specifically need the 2.5 model:
```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "A simple abstract texture" \
  --output "/path/to/texture.png" \
  --model nano-banana
```

### Using Reference Images

To generate an image based on an existing reference:

```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "Create a similar abstract pattern with warmer colors" \
  --output "/path/to/output.png" \
  --reference "/path/to/reference.png"
```

To use multiple reference images (e.g., blend styles from several sources):

```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "Combine the color palette of the first image with the composition of the second" \
  --output "/path/to/output.png" \
  --reference "/path/to/style-ref.png" \
  --reference "/path/to/composition-ref.png"
```

Reference images help Gemini understand the desired style, composition, or visual elements you want in the generated image. When multiple references are provided, all images are sent to the model together.

**Reference image limits:**
- Nano Banana 2: up to 14 references — up to 10 object images + up to 4 character images
- Nano Banana Pro: up to 14 references — up to 6 object images + up to 5 character images + up to 3 style images
- Nano Banana 2 Lite: not optimized for multiple references; use one, or switch to Nano Banana 2
- Nano Banana (legacy): up to 3 reference images

### Step 2: Integrate with Frontend Design

After generating images, incorporate them into frontend code:

**HTML/CSS:**
```html
<img src="./generated-hero.png" alt="Description" class="hero-image" />
```

**React:**
```jsx
import heroImage from './assets/generated-hero.png';
<img src={heroImage} alt="Description" className="hero-image" />
```

**CSS Background:**
```css
.hero-section {
  background-image: url('./generated-hero.png');
  background-size: cover;
  background-position: center;
}
```

## Crafting Effective Prompts

Write detailed, specific prompts for best results:

**Good prompt:**
> A minimalist geometric pattern with overlapping translucent circles in coral, teal, and gold on a deep navy background, suitable for a modern fintech landing page hero section

**Avoid vague prompts:**
> A nice background image

### Prompt Elements to Include

1. **Subject**: What the image depicts
2. **Style**: Artistic style (minimalist, abstract, photorealistic, illustrated)
3. **Colors**: Specific color palette matching the design system
4. **Mood**: Atmosphere (professional, playful, elegant, bold)
5. **Context**: How it will be used (hero image, icon, texture, illustration)
6. **Technical**: Aspect ratio needs, transparency requirements

## Integration with Frontend-Design Skill

When used alongside the frontend-design skill:

1. **Plan the visual hierarchy** - Identify where generated images add value
2. **Match the aesthetic** - Ensure prompts align with the chosen design direction (brutalist, minimalist, maximalist, etc.)
3. **Generate images first** - Create visual assets before coding the frontend
4. **Reference in code** - Use relative paths to generated images in your HTML/CSS/React

### Example Workflow

1. User requests a landing page with custom hero imagery
2. Invoke nano-banana to generate the hero image with a prompt matching the design aesthetic
3. Invoke frontend-design to build the page, referencing the generated image
4. Result: A cohesive design with custom AI-generated visuals

## Output Location

By default, save generated images to the project's assets directory:
- `./assets/` for simple HTML projects
- `./src/assets/` or `./public/` for React/Vue projects
- Use descriptive filenames: `hero-abstract-gradient.png`, `icon-user-avatar.png`
