"""Check tonight's overnight low in McDonough, GA and send a freeze alert via ntfy.sh."""

from datetime import datetime, time, timedelta
import json
import os
import time as time_module
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
REQUEST_TIMEOUT_SECONDS = 25
MAX_RETRIES = 3


def fetch_forecast(url: str = FORECAST_URL) -> dict:
    """Fetch hourly temperature forecast JSON from Open-Meteo with retries."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as err:
            last_err = err
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: {err}")
            if attempt < MAX_RETRIES:
                time_module.sleep(5)
    raise RuntimeError(f"Failed to fetch forecast after {MAX_RETRIES} attempts: {last_err}")


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
        dt = datetime.fromisoformat(raw_time).replace(tzinfo=TIMEZONE)
        if window_start <= dt <= window_end:
            overnight_readings.append((float(temp), dt))

    if not overnight_readings:
        raise RuntimeError("No hourly temperature readings found for tonight's window.")

    return min(overnight_readings, key=lambda item: item[0])


def send_ntfy_alert(topic: str, min_temp: float, min_time: datetime) -> None:
    """Send a high-priority push notification via ntfy.sh with retries."""
    url = f"https://ntfy.sh/{topic}"
    formatted_time = min_time.strftime("%I:%M %p").lstrip("0")
    body = (
        f"McDonough low hits {min_temp:.1f}°F around {formatted_time}. "
        "Cover your outdoor plants!"
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Title": "Freeze Warning Tonight!",
            "Priority": "high",
            "Tags": "snowflake,seedling",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                if response.status >= 400:
                    raise RuntimeError(f"ntfy.sh returned HTTP {response.status}")
                return
        except Exception as err:
            if attempt == MAX_RETRIES:
                raise
            time_module.sleep(3)


def main() -> None:
    topic = os.getenv("NTFY_TOPIC", DEFAULT_NTFY_TOPIC).strip() or DEFAULT_NTFY_TOPIC
    force_test = os.getenv("FORCE_TEST", "false").strip().lower() == "true"

    if force_test:
        min_temp = TEST_LOW_F
        min_time = datetime.now(TIMEZONE).replace(hour=4, minute=0, second=0, microsecond=0)
        if min_time <= datetime.now(TIMEZONE):
            min_time += timedelta(days=1)
        print(f"FORCE_TEST enabled: simulating overnight low of {min_temp:.1f}°F.")
        send_ntfy_alert(topic, min_temp, min_time)
        print(f"Test freeze notification sent to ntfy.sh/{topic}.")
        return

    forecast = fetch_forecast()
    min_temp, min_time = find_overnight_low(forecast)
    formatted_time = min_time.strftime("%I:%M %p").lstrip("0")

    if min_temp <= FREEZE_THRESHOLD_F:
        print(
            f"Freeze warning triggered (Low: {min_temp:.1f}°F at {formatted_time}). "
            f"Sending alert to ntfy.sh/{topic}..."
        )
        send_ntfy_alert(topic, min_temp, min_time)
        print("Notification sent.")
    else:
        print(f"Safe tonight (Low: {min_temp:.1f}°F at {formatted_time}). No notification sent.")


if __name__ == "__main__":
    main()
