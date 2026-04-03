# Control Cards

These PNGs are the printable EPIC-4 validation control cards.
They pair the control QR payloads from [docs/qr codes/control](/Users/markus/Workspace/jukebox/docs/qr%20codes/control) with the printable card layout from `scripts/generate_validation_cards.py`.

## Regeneration Workflow

Refresh the QR SVG set first:

```sh
python3 scripts/generate_validation_qrs.py
```

Then regenerate the printable PNG cards:

```sh
python3 scripts/generate_validation_cards.py
```

The current defaults write back into the checked-in asset folders:

- QR SVGs: `docs/qr codes/control`
- Printable PNGs: `docs/control cards`

## Rasterization Notes

The printable-card generator renders SVG first and then rasterizes to PNG.
On macOS it tries:

1. `sips`
2. `qlmanage` (Quick Look) as a fallback

In practice, these control-card SVGs may require the `qlmanage` fallback even when `sips` is installed.
If PNG generation fails from a sandboxed or headless tool session, rerun the command from a normal macOS shell so Quick Look can perform the conversion.

After regeneration, inspect the asset diff with:

```sh
git diff -- 'docs/qr codes/control' 'docs/control cards'
```
