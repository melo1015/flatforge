# FlatForge Maker 0.3

FlatForge Maker is an early, local-only web interface for the existing rectangular nesting engine. It provides a visual sheet preview, configurable sheet dimensions, margin and spacing, 90-degree rotation, a placed/unplaced summary, and SVG export using millimetres.

## Requirements

- Python 3.11 or newer (the repository CI currently tests Python 3.11 and 3.12).
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
3. Add or edit rectangular parts. Part names must be unique.
4. Choose whether a part may be rotated by 90 degrees.
5. Select **Calcular distribución** to call the existing Python `nest_parts` engine.
6. Inspect the preview, utilization estimate, and any parts that could not be placed.
7. Export SVG and verify dimensions and machine settings in your laser/CNC software before manufacturing.

## Important limitations

- The current engine uses a deterministic shelf/row heuristic for **rectangles**. It is not an optimal nesting solver and does not support arbitrary polygon outlines.
- Utilization is the sum of placed rectangular part areas divided by the full sheet area. The displayed leftover area does not subtract the margin and does not account for kerf, tabs, clamps, grain direction, lead-ins, or machine constraints.
- SVG export includes placed part outlines only. The sheet boundary, margin guide, and preview labels are omitted from the exported cutting paths. SVG dimensions are expressed in `mm`; still verify the import scale in the target software.
- A partial layout can be exported if at least one part fits. Unplaced parts are not included in the SVG.
- This is a prototype, not a certified manufacturing workflow. Always inspect the generated file before cutting.

## Security

The server binds to `127.0.0.1:8787` only. It has no TLS, user authentication, CSRF protection, persistent project storage, or production deployment hardening. Do not change the bind address or expose the port to a LAN or the internet without a separate security review.

## Next steps

- Add polygon outlines and collision-aware nesting.
- Add kerf compensation and toolpath settings as explicit, machine-specific options.
- Improve preview selection, dimensions, and warnings.
- Add import/export for SVG parts and later DXF.
- Add project persistence and end-to-end tests against actual target machines.
