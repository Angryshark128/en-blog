// Rasterise one SVG to PNG with resvg. Used by tools/devto_mcp.py, because dev.to
// proxies every external image through its own imgproxy, which cannot rasterise SVG
// and hands the reader SVG bytes labelled "image/webp".
//
// Usage: node render.mjs <input.svg> <output.png> [zoom]
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Resvg } from "@resvg/resvg-js";

const [input, output, zoom] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: node render.mjs <input.svg> <output.png> [zoom]");
  process.exit(2);
}

// No system fonts exist on the build host, so ship the faces with the tool.
const fonts = dirname(fileURLToPath(import.meta.url));
const svg = readFileSync(input, "utf8");
const resvg = new Resvg(svg, {
  fitTo: { mode: "zoom", value: Number(zoom ?? 2) },
  font: {
    fontFiles: [
      join(fonts, "fonts", "Inter_400Regular.ttf"),
      join(fonts, "fonts", "Inter_600SemiBold.ttf"),
    ],
    loadSystemFonts: false,
    defaultFontFamily: "Inter",
    sansSerifFamily: "Inter",
  },
});

writeFileSync(output, resvg.render().asPng());
