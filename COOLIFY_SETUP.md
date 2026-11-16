# Job Apply — Coolify deployment notes

The production web container is built from `Dockerfile.web` and runs
`scripts/start_web_production.sh`. At startup, that script applies Alembic
migrations before launching the FastAPI application.

## Required runtime variables

Configure these in Coolify's environment variables. Keep secret values in
Coolify; never commit them to this repository.

- `DATABASE_URL` — PostgreSQL connection string available to the application.
- `WEB_ACCESS_TOKEN` — required access token (or configure the login pair).
- `WEB_USER_ID` — identifier for the candidate workspace.
- `OPENAI_API_KEY` — required for AI analysis and document generation.
- `ATS_SCHEDULER_ENABLED=true` — enables scheduled offer collection.
- `ATS_SCHEDULER_TIMES=08:30,18:30` — collection schedule in Europe/Paris.
- `APEC_WINDOW_HOURS=72` — recent APEC publications to collect.

The exact database hostname and credentials are managed by Coolify and should
not be copied into source files or shared logs.

## Deployment check

1. Confirm the application is connected to the intended Git branch and Dockerfile.
2. Configure required variables in Coolify without printing secret values.
3. Deploy and confirm the service health check at `/ready`.
4. Review deployment logs for successful migration and application startup.
5. Check the Job Apply radar for offers published in the last 72 hours and
   confirm APEC and Business France collection timestamps.

Do not troubleshoot PostgreSQL by exposing its public proxy or placing
credentials in this repository. Run database diagnostics from inside the
Coolify network using its secret-managed connection settings.

