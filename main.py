import sys
from agroclima.app import run
from agroclima.paths import AppPaths

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--weather-check":
        from agroclima.services.weather_diagnostics import run_weather_check

        raise SystemExit(run_weather_check(sys.argv[2]))
    raise SystemExit(run(AppPaths.discover().root))
