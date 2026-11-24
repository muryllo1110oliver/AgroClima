import csv
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import sqlite3
import logging
from ..protocol import Reading

COLUMNS = "ts,soil_moisture,air_temp,air_humidity,light_pct,rain_forecast_mm,rain_sensor_pct,pump,shade,source"


class Database:
    """Persistência SQLite, consultas e exportação em uma única camada."""

    @contextmanager
    def connect(self):
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=10)
            with connection:
                yield connection
        except sqlite3.Error as exc:
            logging.getLogger(__name__).error(
                "Erro no banco SQLite: %s", type(exc).__name__
            )
            raise
        finally:
            if connection is not None:
                connection.close()

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self):
        with self.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    soil_moisture REAL NOT NULL,
                    air_temp REAL NOT NULL,
                    air_humidity REAL NOT NULL,
                    light_pct REAL NOT NULL,
                    rain_forecast_mm REAL NOT NULL,
                    rain_sensor_pct REAL NOT NULL,
                    pump INTEGER NOT NULL,
                    shade INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    raw TEXT
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings(ts)")

    def insert(self, r: Reading):
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO readings
                (ts, soil_moisture, air_temp, air_humidity, light_pct,
                 rain_forecast_mm, rain_sensor_pct, pump, shade, source, raw)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    r.timestamp.isoformat(timespec="seconds"),
                    r.soil_moisture,
                    r.air_temp,
                    r.air_humidity,
                    r.light_pct,
                    r.rain_forecast_mm,
                    r.rain_sensor_pct,
                    int(r.pump),
                    int(r.shade),
                    r.source,
                    r.raw,
                ),
            )

    def recent(self, limit: int = 500) -> list[tuple]:
        with self.connect() as con:
            return con.execute(
                """
                SELECT ts, soil_moisture, air_temp, air_humidity, light_pct,
                       rain_forecast_mm, rain_sensor_pct, pump, shade, source
                FROM readings ORDER BY id DESC LIMIT ?
            """,
                (limit,),
            ).fetchall()[::-1]

    def stats(self) -> dict:
        with self.connect() as con:
            row = con.execute("""
                SELECT COUNT(*), MIN(ts), MAX(ts),
                       AVG(soil_moisture), MIN(soil_moisture), MAX(soil_moisture),
                       AVG(air_temp), MIN(air_temp), MAX(air_temp),
                       AVG(air_humidity), MIN(air_humidity), MAX(air_humidity),
                       AVG(light_pct), AVG(rain_forecast_mm),
                       SUM(pump), SUM(shade)
                FROM readings
            """).fetchone()
        keys = [
            "count",
            "first_ts",
            "last_ts",
            "soil_avg",
            "soil_min",
            "soil_max",
            "temp_avg",
            "temp_min",
            "temp_max",
            "hum_avg",
            "hum_min",
            "hum_max",
            "light_avg",
            "rain_avg",
            "pump_samples",
            "shade_samples",
        ]
        return dict(zip(keys, row))

    def export_csv(self, path):
        self.export_filtered(path)
        return path

    def count(self):
        with self.connect() as con:
            return con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]

    def query(self, start=None, end=None, source=None, search="", limit=None, offset=0):
        clauses = []
        args = []
        for sql, value in [("ts >= ?", start), ("ts < ?", end), ("source = ?", source)]:
            if value is not None:
                clauses.append(sql)
                args.append(value)
        if search:
            clauses.append("(ts LIKE ? OR source LIKE ?)")
            args.extend(["%" + search + "%"] * 2)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connect() as con:
            con.execute("BEGIN")  # A contagem e as linhas pertencem ao mesmo snapshot.
            count = con.execute(
                "SELECT COUNT(*) FROM readings" + where, args
            ).fetchone()[0]
            sql = "SELECT " + COLUMNS + " FROM readings" + where + " ORDER BY ts,id"
            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                args.extend([limit, offset])
            return con.execute(sql, args).fetchall(), count

    def export_filtered(self, path, **filters):
        rows, _ = self.query(**filters)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    "data_hora",
                    "umidade_solo_pct",
                    "temperatura_ar_c",
                    "umidade_ar_pct",
                    "luminosidade_pct",
                    "chuva_prevista_mm",
                    "sensor_chuva_pct",
                    "bomba",
                    "sombreamento",
                    "fonte",
                ]
            )
            writer.writerows(rows)
        return len(rows)


def summarize(rows, interval=1):
    result = dict(
        count=len(rows), pump_events=0, shade_events=0, pump_seconds=0, last_pump="—"
    )
    sources = set(r[9] for r in rows)
    if len(sources) > 1:
        parts = [
            summarize([r for r in rows if r[9] == source], interval)
            for source in sources
        ]
        for key in ("pump_events", "shade_events", "pump_seconds"):
            result[key] = sum(p[key] for p in parts)
        times = [p["last_pump"] for p in parts if p["last_pump"] != "—"]
        result["last_pump"] = max(times) if times else "—"
        return result
    previous = None
    for r in rows:
        if previous and r[9] == previous[9]:
            gap = (
                datetime.fromisoformat(r[0]) - datetime.fromisoformat(previous[0])
            ).total_seconds()
            continuous = 0 <= gap <= max(5, interval * 3)
        else:
            gap = 0
            continuous = False
        if r[7] and (not continuous or not previous[7]):
            result["pump_events"] += 1
            result["last_pump"] = r[0][11:19]
        if r[8] and (not continuous or not previous[8]):
            result["shade_events"] += 1
        if continuous and previous[7]:
            result["pump_seconds"] += gap
        previous = r
    return result
