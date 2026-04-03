# Control QR Codes

These SVG QR codes are generated from the exact payloads used in the EPIC-4 control-card validation flow.
Printable PNG card outputs and rasterization notes live in [docs/control cards/README.md](/Users/markus/Workspace/jukebox/docs/control%20cards/README.md).

Files in this directory:

- `control-smoke-track.svg`
  Payload: `spotify:track:6rqhFgbbKwnb9MLmUQDhG6`
- `control-fallback-album.svg`
  Payload: `spotify:album:1ATL5GLyefJaxhQzSPVrLX`
- `control-fallback-playlist.svg`
  Payload: `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`
- `control-playback-stop.svg`
  Payload: `jukebox:playback:stop`
- `control-playback-next.svg`
  Payload: `jukebox:playback:next`
- `control-mode-replace.svg`
  Payload: `jukebox:mode:replace`
- `control-mode-queue.svg`
  Payload: `jukebox:mode:queue`
- `control-volume-low.svg`
  Payload: `jukebox:volume:low`
- `control-volume-medium.svg`
  Payload: `jukebox:volume:medium`
- `control-volume-high.svg`
  Payload: `jukebox:volume:high`
- `control-setup-wifi-reset.svg`
  Payload: `jukebox:setup:wifi-reset`
- `control-setup-receiver-reauth.svg`
  Payload: `jukebox:setup:receiver-reauth`
- `control-system-shutdown.svg`
  Payload: `jukebox:system:shutdown`

Regenerate them with:

```sh
python3 scripts/generate_validation_qrs.py
```
