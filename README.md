# GroundBook

A municipal sports-complex booking API and wall planner. This deployment setup is designed for the office PC: restarting or recreating the container must not erase Saturday's bookings.

## Run with Docker (persistent data)

Docker stores the SQLite database in `/data/groundbook.db`. `/data` is a named volume, so the database survives container removal and recreation.

1. Copy the example configuration and adjust it if needed:

   ```bash
   cp .env.example .env
   ```

2. Build the image:

   ```bash
   docker build -t groundbook .
   ```

3. Create the persistent volume once:

   ```bash
   docker volume create groundbook-data
   ```

4. Start the application, passing configuration at runtime (not baked into the image):

   ```bash
   docker run -d --name groundbook \
     --env-file .env \
     -p 8080:8080 \
     -v groundbook-data:/data \
     groundbook
   ```

Open `http://<office-pc-ip>:8080/` from the office PC or gate tablet. API docs are at `/docs`; health is at `/healthz`.

### Prove the restart/recreate requirement

Create a booking through the UI or `POST /bookings`, and save the returned `booking_id`. Then remove and recreate the container using the *same* volume:

```bash
docker rm -f groundbook
docker run -d --name groundbook \
  --env-file .env \
  -p 8080:8080 \
  -v groundbook-data:/data \
  groundbook
```

Verify the booking is still present:

```bash
curl -i http://localhost:8080/bookings/<booking_id>
```

The expected result is `HTTP/1.1 200 OK` with the booking and its event timeline. Do not run `docker volume rm groundbook-data`: removing the volume intentionally deletes the persisted database.

### Configuration

All runtime configuration is supplied by `.env` via `--env-file`; `.env` is ignored by Git and excluded from the Docker build context. `.env.example` documents the supported values:

| Variable | Example | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address inside the container |
| `PORT` | `8080` | HTTP port |
| `DATABASE_URL` | `sqlite:////data/groundbook.db` | Database location on the persistent volume |
| `SEED_DIR` | `seed` | Initial grounds and event-type seed files |
| `HOLD_HOURS` | `48` | Requested-booking hold duration |

For example, set `HOLD_HOURS=48` in `.env`, recreate the container, and verify:

```bash
curl -s http://localhost:8080/settings
```

The response includes `"hold_hours": 48`. Existing bookings remain in the same volume.

## One booking: request to the gate

1. A club submits `POST /bookings` with a ground, event type, start/end timestamps and club name.
2. GroundBook validates the interval and opening hours, applies the event type's setup/teardown buffers, and checks that the resulting held interval does not overlap another booking's held interval.
3. On success, the API returns `201 Created`, a booking ID and a `Location` header. The requested booking and its `requested` event are committed to the database in one transaction. `hold_until` is calculated using `HOLD_HOURS`.
4. The office clerk confirms the booking with `POST /bookings/{id}/confirm`. GroundBook rechecks the booking before changing its state and appends a `confirmed` event.
5. The gate tablet reads the day planner from `GET /venues/deccan/grounds/{ground}/day?date=YYYY-MM-DD` and can retrieve the full booking and timeline from `GET /bookings/{id}`. The planner shows the booking and its setup/teardown shadow, so the gate team can see when the ground is held.
6. The event history is append-only. Booking events are logged to stdout, as are every HTTP request, response status and duration. Use `docker logs groundbook` to inspect them:

   ```bash
   docker logs -f groundbook
   ```

The application does not write request/event logs beneath `/app`; Docker captures stdout/stderr.

## Existing application features

- Four grounds with weekday/Sunday hours and six event types, seeded idempotently from `seed/`.
- `POST /bookings`, `GET /bookings/{id}`, confirm, cancel and move operations.
- Setup/teardown buffers and overlap checks against the full held interval.
- Append-only booking event timeline; database triggers reject event updates/deletes.
- `GET /settings` reports the configured hold duration and live buffer table.

## Run locally

The container default database path is `/data/groundbook.db`. For local development, set a writable database URL in your shell or `.env`, for example `DATABASE_URL=sqlite:///./groundbook.db`, then run:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
python -m uvicorn groundbook.app:app --host 127.0.0.1 --port 8080
python -m pytest
```

On Windows, activate `.venv\\Scripts\\activate` and use `python -m pip` for installation.

## Notes

- The image contains application code and seed data only. Runtime settings come from the env-file.
- The Docker named volume is the persistence boundary. Reuse the same volume when replacing the container.
- Docker image build and volume-recreation checks should be run on a machine with Docker available; do not infer success from the unit test suite alone.

<!-- learntube:start -->
---

[![tests](https://github.com/KUBENDHIRAN-V-B/groundbook-python/actions/workflows/tests.yml/badge.svg)](https://github.com/KUBENDHIRAN-V-B/groundbook-python/actions/workflows/tests.yml)

### Progress

- [x] Ticket 1 · The complex, as a day you can look at
- [x] Ticket 2 · A club asks for a slot
- [x] Ticket 3 · Confirm, cancel, and the hour that has already gone
- [x] Ticket 4 · The refusals, once the shadows are counted
- [x] Ticket 5 · Moving a booking without breaking the day
- [x] Ticket 6 · A planner nobody can erase
- [x] Ticket 7 · One file becomes an app
- [x] Ticket 8 · The rule table, and then the rule changes
- [x] Ticket 9 · It runs on the office machine
- [x] Ticket 10 · It survives being switched off

Built by KUBENDHIRAN V B on [LearnTube Guided Projects](https://guidedprojects.learntube.ai).
<!-- learntube:end -->
