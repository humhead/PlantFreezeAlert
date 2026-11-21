# Plant Freeze Alert

A zero-dependency Python script and GitHub Actions workflow that checks tonight's overnight low temperature (6:00 PM – 8:00 AM ET) for McDonough, GA using the free [Open-Meteo API](https://open-meteo.com/) and sends a push notification via [ntfy.sh](https://ntfy.sh/) if temperatures are forecast to hit **32.0°F or below**.

## Files

- `check_freeze.py` — Uses only Python's standard library (`urllib.request`, `json`, `os`, `datetime`, `zoneinfo`) to check the overnight forecast and notify via `ntfy.sh`.
- `.github/workflows/freeze_check.yml` — Runs automatically every evening at `22:15 UTC` (5:15 PM EST / 6:15 PM EDT) and supports on-demand manual runs.

## Receive Notifications on Your Phone

1. Install the **ntfy** app on iOS or Android (or open `https://ntfy.sh/humhead-plants-30252` in a browser).
2. Tap **+** and subscribe to topic: `humhead-plants-30252`.

## How to Run a Manual Test from GitHub

1. Push this repository to GitHub.
2. Open your repository on GitHub and click the **Actions** tab.
3. In the left sidebar, select **Plant Freeze Alert**.
4. Click the **Run workflow** dropdown button on the right.
5. Check the box for **Simulate a 28.0°F freeze alert to test ntfy.sh** (`force_test`).
   - Leave it unchecked if you want to run a real check against tonight's live forecast.
6. Click **Run workflow**.
7. Within a few seconds, your phone should receive a high-priority **"Freeze Warning Tonight!"** notification simulating a `28.0°F` low.

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `NTFY_TOPIC` | `humhead-plants-30252` | The ntfy.sh topic to post alerts to. |
| `FORCE_TEST` | `false` | Set to `true` to simulate a `28.0°F` low and force a test notification. |
