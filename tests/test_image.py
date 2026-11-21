"""The image recipe and the health call. The build itself and the calls from another host are run by hand
with docker; what can be checked in-process is here."""
"""The container image contract: health, routes, Dockerfile and complete pinned dependencies."""
import re

from tests.conftest import ROOT, V


def test_health_is_up(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert len(client.get(f"{V}/grounds").json()["grounds"]) == 4, "the list the gate tablet reads first"


def test_dockerfile_matches_the_contract_and_takes_host_and_port_from_the_environment():
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    assert "FROM python:3.12-slim" in lines and "RUN pip install --no-cache-dir -r requirements.lock" in lines
    assert "VOLUME [\"/data\"]" in lines
    assert "RUN mkdir -p /data" in lines
    assert "EXPOSE 8080" in lines
    cmd = [line for line in lines if line.startswith("CMD")]
    assert len(cmd) == 1 and r'\"${HOST:-0.0.0.0}\"' in cmd[0] and r'\"${PORT:-8080}\"' in cmd[0], cmd
    assert "COPY groundbook ./groundbook" in lines and "COPY seed ./seed" in lines and not any(line.startswith("COPY . ") for line in lines)
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=sqlite:////data/groundbook.db" in env_example
    assert "HOLD_HOURS=24" in env_example
    assert ".env" in (ROOT / ".dockerignore").read_text(encoding="utf-8")


def test_the_lock_pins_every_package_the_image_installs():
    lock = [line for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][\w.]*", line) for line in lock), lock
    names = {line.split("==")[0].lower() for line in lock}
    assert {"fastapi", "uvicorn", "sqlalchemy", "pydantic", "pydantic-settings", "starlette", "pydantic-core", "anyio", "h11", "click"} <= names
    assert len(lock) == 17
    top = (ROOT / "requirements.txt").read_text(encoding="utf-8").split()
    assert top == ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "pydantic-settings"]


def test_booking_survives_app_recreation_with_the_same_database(tmp_path):
    from fastapi.testclient import TestClient
    from groundbook.app import create_app
    from groundbook.settings import Settings

    database = (tmp_path / "persistent.db").as_posix()
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{database}",
        seed_dir=str(ROOT / "seed"),
    )
    with TestClient(create_app(settings)) as first:
        created = first.post("/bookings", json={
            "ground": "A",
            "event": "league",
            "from": "2099-10-03T14:00:00Z",
            "to": "2099-10-03T17:00:00Z",
            "club": "Saturday Club",
        })
        assert created.status_code == 201, created.text
        booking_id = created.json()["booking_id"]

    # A fresh app/engine simulates the process/container being replaced while the DB file remains.
    with TestClient(create_app(settings)) as second:
        restored = second.get(f"/bookings/{booking_id}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["booking_id"] == booking_id
        assert restored.json()["events"][0]["kind"] == "requested"


def test_env_file_configuration_is_loaded(tmp_path):
    from groundbook.settings import Settings

    env_file = tmp_path / "office.env"
    env_file.write_text("HOLD_HOURS=48\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    assert settings.hold_hours == 48
