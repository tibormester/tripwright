from __future__ import annotations

from pathlib import Path

STATIC_UI_DIR = Path(__file__).resolve().parent / "static" / "ui"

SVG_TEMPLATE = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"256\" height=\"256\" viewBox=\"0 0 256 256\" fill=\"none\">
  <defs>
    <radialGradient id=\"bg\" cx=\"0\" cy=\"0\" r=\"1\" gradientUnits=\"userSpaceOnUse\" gradientTransform=\"translate(86 70) rotate(50) scale(210 210)\">
      <stop offset=\"0\" stop-color=\"{bg_top}\"/>
      <stop offset=\"1\" stop-color=\"{bg_bottom}\"/>
    </radialGradient>
    <filter id=\"shadow\" x=\"-20%\" y=\"-20%\" width=\"140%\" height=\"140%\">
      <feDropShadow dx=\"0\" dy=\"10\" stdDeviation=\"10\" flood-color=\"{shadow_color}\" flood-opacity=\"0.42\"/>
    </filter>
  </defs>

  <circle cx=\"128\" cy=\"128\" r=\"118\" fill=\"url(#bg)\" stroke=\"{ring_color}\" stroke-width=\"6\"/>
  <ellipse cx=\"128\" cy=\"207\" rx=\"72\" ry=\"22\" fill=\"{base_shadow}\" opacity=\"0.4\"/>

  <g filter=\"url(#shadow)\">
    <circle cx=\"128\" cy=\"95\" r=\"41\" fill=\"{silhouette}\"/>
    <path d=\"M64 198c0-35.346 28.654-64 64-64s64 28.654 64 64v9H64v-9Z\" fill=\"{silhouette}\"/>
  </g>

  <path d=\"M48 210c21-17 48-26 80-26 33 0 61 9 82 26\" stroke=\"{highlight}\" stroke-opacity=\"0.3\" stroke-width=\"4\" stroke-linecap=\"round\"/>
</svg>
"""

ASSETS = {
    "narrator-avatar.svg": {
        "bg_top": "#f1ead9",
        "bg_bottom": "#b4a186",
        "ring_color": "#e7dcc4",
        "shadow_color": "#3f3022",
        "base_shadow": "#4b3929",
        "silhouette": "#6d5a49",
        "highlight": "#fff7e9",
    },
    "user-avatar.svg": {
        "bg_top": "#eadcc4",
        "bg_bottom": "#9d7d5d",
        "ring_color": "#e8d6bb",
        "shadow_color": "#342315",
        "base_shadow": "#473123",
        "silhouette": "#5c4330",
        "highlight": "#fff2dc",
    },
}


def main() -> None:
    STATIC_UI_DIR.mkdir(parents=True, exist_ok=True)

    for filename, palette in ASSETS.items():
        content = SVG_TEMPLATE.format(**palette)
        output_path = STATIC_UI_DIR / filename
        output_path.write_text(content, encoding="utf-8")
        print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
