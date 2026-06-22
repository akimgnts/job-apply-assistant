# Coolify PostgreSQL Public Proxy Setup

## Problem

The Coolify PostgreSQL database is not accepting connections from outside Coolify's network using the public proxy (37.59.112.53:5432).

**Error**: `FATAL: password authentication failed for user "postgres"`

---

## Diagnosis

✓ Network connectivity working (connection attempts reach server)
✓ Password format correct
✗ Authentication failing (credentials rejected)

This suggests one of:
1. Public proxy requires different credentials than internal access
2. Public proxy not fully configured/enabled
3. Database user doesn't have public access permissions
4. Database needs to be created separately

---

## Steps to Resolve

### 1. Check Coolify Dashboard Settings

In your Coolify dashboard, navigate to:
- **Services** → **PostgreSQL Database** → **Settings**

Look for:
- [ ] **Public proxy enabled** checkbox (must be ON)
- [ ] **Public proxy port**: Should be 5432
- [ ] **Public proxy authentication**: Check if different from internal
- [ ] **Database user credentials**: Verify username/password

**If public proxy is NOT enabled**:
- Click "Enable Public Proxy"
- Wait 1-2 minutes for configuration to apply
- Try connecting again

### 2. Check Database Access Permissions

In Coolify, verify:
- [ ] Database user "postgres" has access to the initial database
- [ ] No additional authentication required
- [ ] Check if separate database needs to be created

**Steps**:
1. Click on the PostgreSQL service
2. Go to "Services" or "Databases" tab
3. Check if there's a separate database (not just "postgres")
4. Verify user permissions for public access

### 3. Verify Connection String Components

Your current `.env` has:
```
USER: postgres
HOST: 37.59.112.53
PORT: 5432
DATABASE: postgres
PASSWORD: K5InfD88xGYxS3dUFr210Jmu1SgKzxTTxpqsgQ0Ua0dj3W0wQqf7QM5cfL3gAFca
```

**Verify each component**:
- [ ] Is the IP address `37.59.112.53` correct?
- [ ] Is the port really 5432 (not 3000 or other)?
- [ ] Is the database name really "postgres" (not "job_apply_db")?
- [ ] Is the password exactly as shown (no copy-paste issues)?

**To find correct values in Coolify**:
1. Open PostgreSQL service details
2. Look for "Public Proxy" section
3. You should see: Host, Port, Username
4. Copy these values exactly

### 4. Test Connection from Coolify VM

If you have SSH access to the Coolify server, test internally:

```bash
psql -h localhost -U postgres -d postgres
# Enter password when prompted
```

If this works internally, then public proxy might be the issue.

---

## Alternative: Create a New Database User

If the "postgres" user won't work publicly, Coolify might require creating a dedicated user for public access:

1. In Coolify PostgreSQL dashboard
2. Look for "Users" or "Roles" section
3. Create new user (e.g., "job_apply_user")
4. Set strong password
5. Grant permissions to your database
6. Update `.env` with new credentials

---

## Testing Script

Run the diagnostic tool:

```bash
python test_db_connection.py
```

This will test multiple configurations and help identify which specific setting is wrong.

---

## Common Issues & Solutions

### Issue: "Connection refused" on port 3000
**Solution**: Port 3000 is internal Docker mapping. For public access, use port 5432.

### Issue: "Could not translate host name"
**Solution**: The hostname `yde015v0piay27f73rueuayf` is internal. Use public IP `37.59.112.53` instead.

### Issue: "Password authentication failed"
**Likely causes**:
1. Wrong password → Copy from Coolify again, check for special characters
2. Public proxy not enabled → Check Coolify settings
3. Different credentials for public → Create dedicated user with public access
4. Database doesn't exist → Create it in Coolify first

### Issue: "Database 'postgres' does not exist"
**Solution**: The initial database might have a different name. Check Coolify dashboard for actual database name.

---

## Once Connected Successfully

1. Apply migrations:
   ```bash
   alembic upgrade head
   ```

2. Seed profile data:
   ```bash
   python -m app.database.seed_profile
   ```

3. Start the bot:
   ```bash
   python -m app.bot.telegram_bot
   ```

---

## Debug Information to Collect

If you contact Coolify support, provide:
- PostgreSQL service name: `postgresql-database-yde0I5v0piay27f73rueuayf`
- Public proxy IP: `37.59.112.53`
- Public proxy port: `5432`
- Error message: `FATAL: password authentication failed for user "postgres"`
- Network: External (trying to connect from outside Coolify)

---

## Quick Checklist

- [ ] Public proxy enabled in Coolify
- [ ] Can access internal database (test via SSH)
- [ ] Public proxy listening on correct port
- [ ] Credentials are exact copy from Coolify
- [ ] Database name is correct
- [ ] Run `python test_db_connection.py` and share results

---

## Contact & Support

If unable to resolve:
1. Check Coolify documentation: https://coolify.io/docs
2. Run diagnostic: `python test_db_connection.py`
3. Review DATABASE_SETUP.md for local fallback
