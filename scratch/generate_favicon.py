"""
Generate ForensiQ Magnifying Glass Favicon
Generates favicon.svg, favicon.png (32x32, 64x64, 128x128), and multi-res favicon.ico
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT_DIR = Path("core/static/core/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Clean Vector SVG
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none">
    <defs>
        <linearGradient id="rimGrad" x1="10" y1="6" x2="44" y2="40" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#fde047"/>
            <stop offset="35%" stop-color="#f59e0b"/>
            <stop offset="100%" stop-color="#ea580c"/>
        </linearGradient>
        <linearGradient id="glassGrad" x1="14" y1="10" x2="38" y2="34" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.45"/>
            <stop offset="100%" stop-color="#0284c7" stop-opacity="0.15"/>
        </linearGradient>
        <linearGradient id="handleGrad" x1="36" y1="36" x2="58" y2="58" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#f59e0b"/>
            <stop offset="40%" stop-color="#c2410c"/>
            <stop offset="100%" stop-color="#7c2d12"/>
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#ea580c" flood-opacity="0.45"/>
        </filter>
    </defs>
    <!-- Handle -->
    <path d="M38 38 L54 54" stroke="url(#handleGrad)" stroke-width="8.5" stroke-linecap="round"/>
    <path d="M40 40 L53 53" stroke="#fef08a" stroke-width="2" stroke-linecap="round" opacity="0.6"/>
    <!-- Glass Fill -->
    <circle cx="26" cy="26" r="18" fill="url(#glassGrad)"/>
    <!-- Outer Rim -->
    <circle cx="26" cy="26" r="18" stroke="url(#rimGrad)" stroke-width="5.5" filter="url(#glow)"/>
    <!-- Inner Lens Gleam -->
    <path d="M15 19 A 14 14 0 0 1 33 13" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" opacity="0.85"/>
    <!-- Forensic Crosshair / Center Target -->
    <circle cx="26" cy="26" r="4.5" stroke="#fde047" stroke-width="1.8" opacity="0.9"/>
    <circle cx="26" cy="26" r="1.5" fill="#fde047"/>
</svg>
"""

svg_path = OUTPUT_DIR / "favicon.svg"
svg_path.write_text(svg_content.strip(), encoding="utf-8")
print(f"[OK] Written {svg_path}")


# 2. Render high-resolution raster image with Pillow (supersampled 4x for crystal clear antialiasing)
def render_magnifying_glass(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Coordinates scaled to canvas
    # Center of lens: (0.41 * canvas_size, 0.41 * canvas_size)
    cx = 0.40 * canvas_size
    cy = 0.40 * canvas_size
    r = 0.28 * canvas_size
    rim_w = max(2, int(0.088 * canvas_size))

    # Handle coordinates
    h_start_x = cx + r * 0.707
    h_start_y = cy + r * 0.707
    h_end_x = 0.88 * canvas_size
    h_end_y = 0.88 * canvas_size
    h_width = max(3, int(0.14 * canvas_size))

    # Draw handle shadow
    draw.line(
        [(h_start_x + scale, h_start_y + scale), (h_end_x + scale, h_end_y + scale)],
        fill=(234, 88, 12, 100),
        width=h_width + scale,
    )
    # Draw handle main
    draw.line(
        [(h_start_x, h_start_y), (h_end_x, h_end_y)],
        fill=(194, 65, 12, 255),
        width=h_width,
    )
    # Handle metallic highlight
    draw.line(
        [
            (h_start_x + scale * 0.5, h_start_y + scale * 0.5),
            (h_end_x - scale * 1.5, h_end_y - scale * 1.5),
        ],
        fill=(254, 240, 138, 200),
        width=max(1, int(h_width * 0.25)),
    )

    # Glass fill (soft sky-blue tint)
    draw.ellipse(
        [cx - r + rim_w // 2, cy - r + rim_w // 2, cx + r - rim_w // 2, cy + r - rim_w // 2],
        fill=(56, 189, 248, 70),
    )

    # Rim shadow / glow
    draw.ellipse(
        [cx - r - scale * 0.5, cy - r + scale * 0.5, cx + r + scale * 0.5, cy + r + scale * 1.5],
        outline=(234, 88, 12, 140),
        width=rim_w + scale,
    )
    # Rim main (vibrant amber / orange)
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(245, 158, 11, 255),
        width=rim_w,
    )
    # Inner rim highlight
    inner_r = r - rim_w // 4
    draw.arc(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        start=170,
        end=290,
        fill=(254, 240, 138, 240),
        width=max(1, int(scale * 1.5)),
    )

    # Lens glare arc
    glare_r = r * 0.72
    draw.arc(
        [cx - glare_r, cy - glare_r, cx + glare_r, cy + glare_r],
        start=195,
        end=275,
        fill=(255, 255, 255, 220),
        width=max(1, int(scale * 1.8)),
    )

    # Central forensic target reticle
    ret_r = max(2, int(r * 0.25))
    draw.ellipse(
        [cx - ret_r, cy - ret_r, cx + ret_r, cy + ret_r],
        outline=(253, 224, 71, 230),
        width=max(1, int(scale * 1.2)),
    )
    center_dot_r = max(1, int(scale * 1.1))
    draw.ellipse(
        [cx - center_dot_r, cy - center_dot_r, cx + center_dot_r, cy + center_dot_r],
        fill=(253, 224, 71, 255),
    )

    # Downsample with high-quality Lanczos filter
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img


# Generate PNGs
png_32 = render_magnifying_glass(32)
png_64 = render_magnifying_glass(64)
png_128 = render_magnifying_glass(128)
png_256 = render_magnifying_glass(256)

png_32.save(OUTPUT_DIR / "favicon-32x32.png", "PNG")
png_64.save(OUTPUT_DIR / "favicon.png", "PNG")
png_128.save(OUTPUT_DIR / "favicon-128x128.png", "PNG")
print(f"[OK] Written PNG favicons to {OUTPUT_DIR}")

# Generate multi-resolution ICO
ico_images = [
    render_magnifying_glass(16),
    render_magnifying_glass(32),
    render_magnifying_glass(48),
    render_magnifying_glass(64),
]
ico_path = OUTPUT_DIR / "favicon.ico"
ico_images[0].save(
    ico_path,
    format="ICO",
    sizes=[(img.width, img.height) for img in ico_images],
    append_images=ico_images[1:],
)
print(f"[OK] Written {ico_path}")
