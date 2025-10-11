# Veoovibes for Home Assistant (custom component)

Custom integration for the **Veoovibes Multiroom Audio System** (inveoo).
Creates **one media player per room** using the official HTTP API (`/api/v1`).

## Features
- One `media_player` per **room** (assign each to a Home Assistant Area)
- **Play / Stop / Next / Previous / Volume (0–100%)**
- Title / Artist / Album / Cover (when provided by `room_player_status`)
- **UI-based setup** (Config Flow)

## Requirements
- Home Assistant 2023.12+ (recommended)
- Veoovibes controller reachable on your LAN
- **API key** (from Veoovibes/System Manager)

## Manual Installation
1. Download this repository as ZIP or clone it.
2. Copy the folder `custom_components/veoovibes` into your HA config:
   ```
   <config>/
   └─ custom_components/
      └─ veoovibes/
          __init__.py
          api.py
          config_flow.py
          const.py
          diagnostics.py
          manifest.json
          media_player.py
          strings.json
          translations/...
   ```
3. **Restart Home Assistant**.
4. Go to **Settings → Devices & Services → Add Integration** and search for **Veoovibes**.
5. Enter **Base URL** (e.g., `http://<controller-ip>`) and **API key**.
   - If using self-signed HTTPS, disable “Verify SSL certificate”.

## HACS Installation (optional)
> Only if you add this repo as a **Custom Repository** in HACS.
1. HACS → Integrations → **Custom repositories** → add your repo URL → Type **Integration**.
2. Install **Veoovibes**, **restart HA**, then add it via **Devices & Services**.

## Configuration / Used Endpoints
During setup the integration calls `listrooms`. A `media_player` is created for each room.
- `GET /api/v1/listrooms?api_key=<KEY>`
- `GET /api/v1/room_player_status?api_key=<KEY>&room=<ID>`
- `GET /api/v1/room_play|room_stop|room_next|room_prev|room_vol_set?api_key=<KEY>&room=<ID>[&vol=0..100]`

## Usage
- Assign each `media_player.veoovibes_*` to its matching **Area** in **Settings → Areas**.
- Use standard media controls (Play/Stop/Next/Prev, volume slider).

## Troubleshooting
- **No rooms found:** Open `http://<IP>/api/v1/listrooms?api_key=<KEY>` in a browser.
- **Empty status:** Check `http://<IP>/api/v1/room_player_status?api_key=<KEY>&room=<ID>`.
- **Hostname issues:** Try the **IP address** instead of `*.local`.
- **SSL:** For self-signed certs, disable SSL verification in the setup.

### Enable Debug Logs
```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.veoovibes: debug
```

## Uninstall
Remove the integration in **Settings → Devices & Services**, then delete
`custom_components/veoovibes` and restart Home Assistant.

## Trademark Notice
“Veoovibes” and associated logos are trademarks of **inveoo**.
This integration uses the public HTTP API solely to enable Home Assistant connectivity.
