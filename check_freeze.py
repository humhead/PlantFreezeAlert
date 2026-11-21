"""Check tonight's overnight low in McDonough, GA and send a freeze alert via ntfy.sh."""

from datetime import datetime, time, timedelta
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=33.4473"
    "&longitude=-84.1469"
    "&hourly=temperature_2m"
    "&temperature_unit=fahrenheit"
    "&timezone=America%2FNew_York"
    "&forecast_days=2"
)
TIMEZONE = ZoneInfo("America/New_York")
FREEZE_THRESHOLD_F = 32.0
TEST_LOW_F = 28.0
DEFAULT_NTFY_TOPIC = "humhead-plants-30252"
REQUEST_TIMEOUT_SECONDS = 30


def fetch_forecast(url: str = FORECAST_URL) -> dict:
    """Fetch hourly temperature forecast JSON from Open-Meteo."""
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def find_overnight_low(
    forecast: dict, now: datetime | None = None
) -> tuple[float, datetime]:
    """Return (min_temp_f, timestamp) for 6:00 PM today through 8:00 AM tomorrow (ET)."""
    current_et = (now or datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    today = current_et.date()

    window_start = datetime.combine(today, time(18, 0), tzinfo=TIMEZONE)
    window_end = datetime.combine(
        today + timedelta(days=1), time(8, 0), tzinfo=TIMEZONE
    )

    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])

    overnight_readings: list[tuple[float, datetime]] = []
    for raw_time, temp in zip(times, temps):
        if temp is None:
            continue
        reading_dt = datetime.fromisoformat(raw_time).replace(tzinfo=TIMEZONE)
        if window_start <= reading_dt <= window_end:
            overnight_readings.append((float(temp), reading_dt))

    if not overnight_readings:
        raise ValueError(
            f"No forecast temperatures found between {window_start.isoformat()} "
            f"and {window_end.isoformat()}."
        )

    return min(overnight_readings, key=lambda reading: reading[0])


def format_hour(dt: datetime) -> str:
    """Format a datetime as a clean 12-hour clock time (e.g. '4:00 AM')."""
    return dt.strftime("%I:%M %p").lstrip("0")


def send_ntfy_alert(topic: str, min_temp: float, min_time: str) -> None:
    """Send a freeze warning push notification via ntfy.sh."""
    url = f"https://ntfy.sh/{topic}"
    body = (
        f"McDonough low hits {min_temp:.1f}°F around {min_time}. "
        "Cover your outdoor plants!"
    )
    request = urllib.request.Request(
        url=url,
        data=body.encode("utf-8"),
        method="POST",
        headers={
            "Title": "Freeze Warning Tonight!",
            "Priority": "high",
            "Tags": "snowflake,seedling",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        response.read()


def main() -> None:
    ntfy_topic = os.environ.get("NTFY_TOPIC") or DEFAULT_NTFY_TOPIC
    force_test = os.environ.get("FORCE_TEST", "false").strip().lower() == "true"

    forecast = fetch_forecast()
    min_temp, min_dt = find_overnight_low(forecast)
    min_time = format_hour(min_dt)

    if force_test:
        print(
            f"FORCE_TEST enabled (actual forecast low: {min_temp:.1f}°F around {min_time}). "
            f"Simulating {TEST_LOW_F:.1f}°F freeze alert."
        )
        min_temp = TEST_LOW_F

    if min_temp <= FREEZE_THRESHOLD_F or force_test:
        send_ntfy_alert(ntfy_topic, min_temp, min_time)
        print(
            f"Freeze alert sent to ntfy.sh/{ntfy_topic} "
            f"(Low: {min_temp:.1f}°F around {min_time})."
        )
    else:
        print(f"Safe tonight (Low: {min_temp:.1f}°F). No notification sent.")


if __name__ == "__main__":
    main()
