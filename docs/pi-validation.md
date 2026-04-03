# Raspberry Pi Validation

This document defines the EPIC 4 validation stack for the Raspberry Pi appliance.
It extends the EPIC 3 reboot, recovery, and scan-to-playback baseline with the new operator surface, control cards, setup or auth flows, automatic Wi-Fi fallback, and idle shutdown behavior.

Use [docs/pi-setup-log.md](/Users/markus/Workspace/jukebox/docs/pi-setup-log.md) to record the exact Pi, image, and validation outcome for each run.

## Validation QR Payloads

The exact validation QR payloads are:

- Smoke track: `spotify:track:6rqhFgbbKwnb9MLmUQDhG6`
- Queue-fallback album: `spotify:album:1ATL5GLyefJaxhQzSPVrLX`
- Queue-fallback playlist: `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`
- Stop: `jukebox:playback:stop`
- Next: `jukebox:playback:next`
- Mode replace: `jukebox:mode:replace`
- Mode queue: `jukebox:mode:queue`
- Volume low: `jukebox:volume:low`
- Volume medium: `jukebox:volume:medium`
- Volume high: `jukebox:volume:high`
- Wi-Fi reset: `jukebox:setup:wifi-reset`
- Receiver re-auth: `jukebox:setup:receiver-reauth`
- Shutdown: `jukebox:system:shutdown`

Generated QR images for those payloads live under [spec/qr codes/control](/Users/markus/Workspace/jukebox/spec/qr%20codes/control), and printable command cards live under [spec/control cards](/Users/markus/Workspace/jukebox/spec/control%20cards).

## Remote Smoke Validation

Use the smoke helper for repeatable remote checks:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_PI_RECEIVER_SERVICE_NAME=spotifyd.service \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
JUKEBOX_SMOKE_ACTION_PAYLOAD='jukebox:mode:queue' \
./scripts/pi-smoke.sh
```

Expected remote checks:

- `spotifyd.service` is active.
- `jukebox.service` is active.
- recent `journalctl` output is readable for both services.
- the operator `status.json` endpoint is readable before the system is treated as ready.
- a one-shot stdin replay for a Spotify card reaches a playback or queue success line.
- an optional action-card stdin replay reaches an `[ACTION]` line.

Treat the remote snapshot as the service-owned diagnostic surface.
At minimum, verify that `status.json` includes:

- `feedback.display_state`
- `feedback.message`
- `runtime.playback_mode`
- `runtime.setup_required`
- `runtime.auth_required`
- `runtime.enabled_actions`
- `runtime.scanner`
- `runtime.playback`
- `runtime.setup`
- `runtime.config`
- `runtime.idle`

Also verify that `status.json` does not expose:

- Spotify client secret or refresh token
- Wi-Fi passphrase
- receiver credential-file contents

Interpret the status carefully:

- `runtime.setup_required = true` means the box is intentionally in setup access mode, not ordinary playback-ready mode.
- `runtime.auth_required = true` means the browser auth path must complete before the appliance should be treated as ready.
- `runtime.playback.code = receiver_unavailable` means the controller can talk to Spotify but the target receiver is not visible.
- `runtime.playback.code = controller_auth_unavailable` means the Python app's own Spotify controller credentials are broken even if `spotifyd` is running.
- `runtime.playback.code = network_unavailable` means Wi-Fi, DNS, or upstream Spotify reachability is broken.
- `runtime.idle.shutdown_requested = true` means the service has already requested an idle shutdown and the unit should be allowed to power off cleanly.

## Manual Control-Card Validation

Run these checks on the physical prototype with real cards:

1. Confirm an ordinary Spotify track card still starts playback.
2. Confirm duplicate suppression still blocks an immediate repeated scan of the same Spotify card.
3. Confirm `jukebox:playback:stop` pauses active playback.
4. Confirm `jukebox:playback:next` advances to the next track during active playback.
5. Confirm `jukebox:mode:queue` changes `runtime.playback_mode` to `queue_tracks`.
6. In queue mode, confirm a real track card queues during active playback, and starts playback in case the player is idle.
7. In queue mode, confirm an album or playlist card still replaces playback and emits the explicit fallback event.
8. Confirm each selected volume preset card applies the configured software volume percentage without changing the external-speaker baseline.
9. Confirm `jukebox:system:shutdown` triggers a graceful shutdown path rather than an abrupt power cut.
10. Double-scan one operator-facing card such as Wi-Fi reset or shutdown and confirm the second scan is suppressed by the control debounce window.

## Manual Setup and Auth Validation

Validate the operator-maintenance flow from another device on the same network or setup AP:

1. Open the operator surface at `http://<pi-host>:<operator-port>/`.
2. Confirm `GET /status.json` shows the same readiness state the terminal and logs show.
3. Open `/wifi` and submit a test network through the documented setup flow.
4. Confirm the helper result is surfaced through the browser path without shell-only steps.
5. Scan `jukebox:setup:wifi-reset` and confirm the runtime enters `setup_required`.
6. Confirm the Pi re-enters setup AP mode and the operator surface stays reachable there.
7. Scan `jukebox:setup:receiver-reauth` and confirm the runtime enters `auth_required`.
8. Open `/auth`, start the auth flow, and confirm the browser-visible flow surfaces the approval state or approval URL.
9. Confirm the runtime stays in `auth_required` until auth succeeds and the receiver becomes visible again.
10. After auth succeeds, confirm the runtime returns to `ready` without source edits or machine-specific credential copying.

## Automatic Wi-Fi Fallback Validation

EPIC 4 fallback behavior is intentionally narrow.
Validate both the positive and negative cases:

1. Boot the Pi with no usable client Wi-Fi configuration and confirm it enters setup AP mode automatically.
2. Boot the Pi with a saved but unreachable client network and confirm it enters setup AP mode only after the configured fallback grace period elapses.
3. Boot the Pi with a temporarily slow but ultimately reachable network and confirm it returns to client mode within the grace period instead of switching to setup AP mode.
4. After the appliance has already reached `ready`, interrupt the network briefly and confirm it stays in degraded recovery instead of immediately switching to setup AP mode.

Record the configured grace-period value used for the test and whether the observed timing matched it closely enough to trust the behavior.

## Idle Shutdown Validation

Idle shutdown must stay conservative:

1. Set `JUKEBOX_IDLE_SHUTDOWN_SECONDS` to a short test value.
2. Confirm idle shutdown does not trigger while playback is active.
3. Confirm idle shutdown does not trigger while player state is unknown or while the runtime is in `setup_required` or `auth_required`.
4. Stop playback and leave the box untouched long enough to exceed the configured idle timeout.
5. Confirm the runtime emits the idle-shutdown request and the Pi shuts down cleanly.
6. Restore power normally and confirm the appliance boots back into the expected ready, degraded, or setup state without manual filesystem repair.

## Scanner and Audio Regression Validation

EPIC 4 does not weaken the EPIC 3 physical baseline.
Rerun these checks after the new setup, control, and shutdown changes:

1. Confirm the mounted scanner reads a real laminated card.
2. Confirm the service logs the scan from the `evdev` source.
3. Confirm the accepted scan reaches playback success rather than only a dispatch attempt.
4. Confirm the external powered speaker remains the baseline audio path.
5. Confirm `speaker-test -c 2 -t wav` and a simple `aplay` sample are still audible before blaming the jukebox app.
6. Confirm a successful scan is audible on the speaker after deployment.

## Reboot, Power-Cycle, and Network Regression Validation

Rerun the carried-forward EPIC 3 reliability checks because EPIC 4 changes touch networking and shutdown:

```sh
JUKEBOX_PI_HOST=jukebox.local \
JUKEBOX_PI_RECEIVER_SERVICE_NAME=spotifyd.service \
JUKEBOX_SMOKE_URI='spotify:track:6rqhFgbbKwnb9MLmUQDhG6' \
JUKEBOX_SMOKE_REBOOT=1 \
JUKEBOX_SMOKE_REBOOT_COUNT=3 \
./scripts/pi-smoke.sh
```

For reboot and power-cycle validation:

1. Confirm both services return after each reboot.
2. Confirm the operator status surface is reachable after each reboot.
3. Confirm the runtime reaches `ready`, `setup_required`, or another explicit state rather than silently hanging.
4. Confirm a fresh scan or stdin replay still works once the runtime is ready.

For temporary network interruption validation:

1. Start from a confirmed `ready` state.
2. Interrupt Wi-Fi or upstream network access briefly.
3. Confirm the runtime surfaces `network_unavailable` or `receiver_unavailable` rather than silently hanging.
4. Restore the network.
5. Confirm the runtime returns to `ready` without restarting the service manually.
6. Run a fresh physical scan or smoke replay after recovery.

## Safe Troubleshooting Order

When the assembled device is not behaving correctly, use this order:

1. Check `systemctl is-active spotifyd.service`.
2. Check `systemctl is-active jukebox.service`.
3. Read the last 50 lines of both journals.
4. Fetch `status.json` and note `feedback.display_state`, `runtime.playback.code`, `runtime.setup_required`, `runtime.auth_required`, and `runtime.idle`.
5. Run `./scripts/pi-smoke.sh`.
6. Only move on to scanner or speaker debugging after the status surface makes the controller-auth, receiver, network, setup, and idle state clear.
