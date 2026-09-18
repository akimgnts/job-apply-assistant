# ATS Daily Scheduler

Automated collection of job offers from all ATS sources with observability and failure isolation.

## Quick Start

### Manual Test Run

```bash
python3 app/scheduler/ats_scheduler.py
```

**Output:**
- Logs: `logs/ats_ingest_YYYY-MM-DD.log` (daily file)
- CSV: `exports/company_hiring_signals.csv` (updated after each run)
- File lock: `/tmp/ats_ingest.lock` (prevents parallel runs)

### Via Cron (Linux/macOS)

```bash
# Add to crontab -e
0 2 * * * cd /path/to/job-apply-assistant && python3 app/scheduler/ats_scheduler.py

# Or with venv
0 2 * * * cd /path/to/job-apply-assistant && /path/to/venv/bin/python3 app/scheduler/ats_scheduler.py
```

Runs daily at 2:00 AM UTC.

### Via Docker

```bash
# Manual run
docker-compose exec app python3 app/scheduler/ats_scheduler.py

# With scheduled restarts (Docker container runs scheduler once, exits)
# Requires external orchestration (e.g., systemd timer, Kubernetes CronJob)
```

### Via systemd Timer (Linux)

**File: `/etc/systemd/system/ats-scheduler.service`**
```ini
[Unit]
Description=ATS Daily Scheduler
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/path/to/job-apply-assistant
Environment="DATABASE_URL=postgresql://jobapply:password@localhost:5432/job_apply_db"
Environment="OPENAI_API_KEY=sk-..."
ExecStart=/path/to/venv/bin/python3 app/scheduler/ats_scheduler.py
User=your_user
```

**File: `/etc/systemd/system/ats-scheduler.timer`**
```ini
[Unit]
Description=ATS Daily Scheduler Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable:**
```bash
sudo systemctl enable --now ats-scheduler.timer
sudo systemctl status ats-scheduler.timer
```

## Observability

### Log Format

Per-source results:
```
2026-09-05 20:28:22,331 [INFO] ats_scheduler:   Created: 0, Duplicates: 47, Snapshots: 1, Duration: 14.3s
```

### Signals CSV

Updated after each run. Key columns:
- `acceleration_score` (0-100): hiring velocity
- `status` (`insufficient_history` | `stable` | `accelerating`)
- `domain_focus`: strongest domain (ai, data, automation, digital)

```
company_id,active_count,new_7d,new_30d,closed_30d,growth_rate,domain_focus,acceleration_score,status
2,47,47,47,0,1.0,ai,80,stable
```

### Failure Handling

- **Source error**: Logged, other sources continue
- **Lock timeout**: Script fails (prevents zombie runs)
- **DB error**: Full rollback, no partial state

## Performance

Typical cycle:
- Lever: ~14s
- Greenhouse: ~44s
- Ashby: ~0.5s
- Business France VIE: ~3s
- **Total: ~2 min**

## Troubleshooting

### "Lock timeout: another process still running"
Check for stuck processes:
```bash
lsof | grep ats_ingest.lock
kill -9 <PID>
rm /tmp/ats_ingest.lock
```

### No new offers created
- Idempotency working correctly (expected after first run)
- Check log for source errors
- Verify offers haven't been scraped yet: `SELECT COUNT(*) FROM job_offers;`

### Signals stay `insufficient_history`
- Normal: need 2+ snapshots spanning 30+ days for trend detection
- After 30 days of daily runs, status will change to `stable` or `accelerating`

## Next: Prospecting

Once 30+ days of data collected:

1. **Export high-signal companies**
   ```bash
   SELECT company_id, acceleration_score FROM company_hiring_signals 
   WHERE acceleration_score > 70 AND status = 'accelerating';
   ```

2. **Map to hiring contacts** (manual, future automation)

3. **Personalize outreach** by domain_focus and specific roles
