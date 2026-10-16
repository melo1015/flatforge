# FlatForge Maker 0.6

FlatForge Maker is an early, local-only web interface for rectangular and simple polygon sheet nesting. It provides a visual sheet preview, configurable sheet dimensions, margin and spacing, 90-degree rotation, a placed/unplaced summary, and SVG export using millimetres.

## Requirements

- Python 3.11 or newer (the repository CI tests Python 3.11 and 3.12).
- No additional Python packages are required to run the local interface.

## Run it

From the repository root:

```bash
python -m flatforge_maker.server
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787).

Stop the server with Ctrl+C.

## Use the workflow

1. Set sheet width and height in millimetres.
2. Set the edge margin and gap between parts.
3. Add or edit rectangular parts, or import simple closed SVG outlines. Imported part dimensions are locked to preserve their contour.
4. Choose whether a part may be rotated by 90 degrees.
5. Select **Calcular distribución** to call the Python `nest_parts` engine.
6. Inspect the preview, utilization estimate, and any parts that could not be placed.
7. Export SVG. The server recalculates the current request and generates the file independently of the preview DOM; verify dimensions and machine settings in your laser/CNC software before manufacturing.

## Importación SVG (0.6)

Use **Importar contornos SVG** to load simple outlines. The importer accepts direct-child `rect`, `polygon`, and explicitly closed `polyline` elements. It rejects DTD/entity declarations, scripts, event handlers, transforms, styles, references, nested groups, malformed geometry, and files over 256 KiB. Imported vertices are normalized and retained for the current session.

The polygon engine uses deterministic vertex-alignment candidates and checks polygon-edge distances to prevent overlap and enforce the configured gap. It supports simple closed polygons without holes and 90-degree rotation. It is a heuristic, not an optimal solver; polygon mode is limited to 100 parts and 5,000 total vertices per request. Curves, holes, SVG paths, arbitrary-angle rotation, kerf compensation, and machine-specific toolpaths are not supported. Inspect exported files in the target CAM software before cutting.

## Nesting algorithm

The engine uses a deterministic **MaxRects-style best-short-side-fit heuristic**. It evaluates both orientations when rotation is enabled, maintains free rectangular regions, and scores candidate placements by the short and long leftover sides. The rectangular implementation is bounded to 500 parts per request. Polygon requests are bounded to 100 parts and 5,000 total vertices.

This is a heuristic, not a proof of optimal packing. Polygon requests use a separate vertex-alignment heuristic for simple, hole-free contours.

## Important limitations

- Utilization is the sum of placed shape areas divided by the full sheet area. The displayed leftover area does not subtract the margin and does not account for kerf, tabs, clamps, grain direction, lead-ins, or machine constraints.
- SVG export is generated server-side from the nesting result and includes placed rectangular or polygonal part contours only, as unfilled black strokes with a nominal 0.1 mm stroke width. The sheet boundary, margin guide, preview labels, and colored preview fills are omitted. The exporter checks that each placement remains within the usable sheet. SVG dimensions are expressed in `mm`; still verify the import scale in the target software.
- A partial layout can be exported if at least one part fits. Unplaced parts are not included in the SVG.
- This is a prototype, not a certified manufacturing workflow. Always inspect the generated file before cutting.

## Security

The server binds to `127.0.0.1:8787` only. It has no TLS, user authentication, CSRF protection, persistent project storage, or production deployment hardening. Do not change the bind address or expose the port to a LAN or the internet without a separate security review.

## Next steps

- Add robust SVG path/curve support, holes, arbitrary-angle rotations, and machine-specific kerf compensation.
- Add machine-specific kerf compensation and toolpath settings.
- Improve preview selection, dimensions, and warnings.
- Add DXF support and project persistence.
- Add browser-driven tests and end-to-end tests against actual target machines.
