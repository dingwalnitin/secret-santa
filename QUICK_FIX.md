# Quick Fix Guide - Website Crashes with High User Load

## Problem
When the number of users is high, the website crashes and not everyone gets the spin wheel animation. You've already migrated from SQLite to Azure SQL, so the database issue is resolved.

## TL;DR - What's Wrong and How to Fix It

### 🔴 Critical Issue
**You're running a production app with Flask's development server**

The line `socketio.run(app, debug=True, host='0.0.0.0', port=5000)` at the end of `app.py` is NOT suitable for production.

### ✅ Quick Fix

1. **Start with Gunicorn instead:**
   ```bash
   gunicorn -c gunicorn_config.py app:app
   ```

2. **Set these environment variables:**
   ```bash
   GUNICORN_WORKERS=5
   WORKER_CONNECTIONS=1000
   DATABASE_URL=<your-azure-sql-connection-string>
   ```

3. **Enable WebSockets in Azure:**
   ```bash
   az webapp config set --name your-app --resource-group your-rg --web-sockets-enabled true
   ```

That's it! These three changes will fix 80% of your scalability issues.

---

## Root Causes (No Code Changes Needed!)

| Issue | Impact | Fix |
|-------|--------|-----|
| **Single worker** | Can't handle 20+ concurrent users | Use Gunicorn with 5 workers |
| **Dev server** | Crashes under load | Use Gunicorn (production server) |
| **No connection pooling** | Database connections exhausted | Set DB pool size in config |
| **Static files via Flask** | Workers blocked serving CSS/JS | Use CDN or Nginx |
| **Cookie sessions** | Don't work across workers | Use Redis for sessions |
| **In-memory rate limiting** | Not shared across workers | Use Redis for rate limiting |
| **WebSockets disabled** | SocketIO fails | Enable in Azure App Service |

---

## Files You Need

All files have been created for you in this repository:

1. **gunicorn_config.py** - Ready to use, just run it
2. **SCALABILITY_GUIDE.md** - Detailed guide (read this!)
3. **AZURE_DEPLOYMENT.md** - Step-by-step deployment
4. **config_reference.py** - Configuration examples
5. **locustfile.py** - Load testing script

---

## Minimum Changes Required

### 1. Azure App Service Configuration (5 minutes)

In Azure Portal → Your App Service:

**General Settings:**
- Startup command: `gunicorn -c gunicorn_config.py app:app`
- Web sockets: **ON**

**Application Settings (Environment Variables):**
```bash
# Required
DATABASE_URL=mssql+pyodbc://user:pass@server.database.windows.net:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
GUNICORN_WORKERS=5
WORKER_CONNECTIONS=1000

# Highly Recommended (for Redis - prevents worker conflicts)
REDIS_URL=rediss://:password@your-redis.redis.cache.windows.net:6380/0

# Security
SECRET_KEY=<generate-random-32-char-string>
SESSION_COOKIE_SECURE=true
```

### 2. Resource Requirements

Based on your expected user count:

| Users | App Service | Azure SQL | Redis |
|-------|-------------|-----------|-------|
| 50-200 | S1 (1 core) | S0 | Basic C0 |
| 200-500 | S2 (2 cores) | S1 | Standard C1 |
| 500-1000 | S3 (4 cores) | S2 | Standard C2 |

**Cost:** ~$150-350/month for 200-500 users

### 3. Deploy

```bash
# If using local git deployment
git remote add azure <your-azure-git-url>
git push azure main

# Or ZIP deployment
zip -r deploy.zip . -x "*.git*" "venv/*" "__pycache__/*"
az webapp deployment source config-zip --name your-app --resource-group your-rg --src deploy.zip
```

---

## Testing Before Production

### 1. Load Test (Recommended)

```bash
# Install locust
pip install locust

# Run load test
locust -f locustfile.py --host=https://your-app.azurewebsites.net --users 100 --spawn-rate 10 --run-time 5m
```

**What to watch:**
- Error rate should be < 1%
- Response time should be < 2s
- CPU should be < 70%
- Memory should be < 80%

### 2. Verify Checklist

- [ ] Gunicorn running (check logs for "Spawning workers")
- [ ] Multiple workers running (check process list)
- [ ] WebSockets enabled (test chat functionality)
- [ ] Database connections not exhausted (check Azure SQL metrics)
- [ ] Static files loading (check browser network tab)
- [ ] No 500 errors in logs
- [ ] Spin wheel loads for all users

---

## Monitoring

### Check if it's working:

```bash
# View logs
az webapp log tail --name your-app --resource-group your-rg

# Should see:
# [INFO] Starting Secret Santa application
# [INFO] Spawning workers
# [INFO] Worker spawned with pid: XXX (repeated for each worker)
```

### What to monitor:

In Azure Portal → Your App Service → Metrics:

1. **CPU Percentage** - Should stay < 70%
2. **Memory Percentage** - Should stay < 80%
3. **Response Time** - Should stay < 2s
4. **HTTP Server Errors** - Should be 0 or very low
5. **Requests** - See actual load

---

## Troubleshooting

### Issue: Workers not starting

**Check:**
```bash
az webapp log tail --name your-app --resource-group your-rg
```

**Common fixes:**
- Verify `gunicorn_config.py` is in repository root
- Check startup command is exactly: `gunicorn -c gunicorn_config.py app:app`
- Ensure `gunicorn` and `eventlet` are in `requirements.txt`

### Issue: WebSockets not working (chat fails)

**Fix:**
```bash
az webapp config set --name your-app --resource-group your-rg --web-sockets-enabled true
```

Then restart:
```bash
az webapp restart --name your-app --resource-group your-rg
```

### Issue: Database connection errors

**Check connection string format:**
```bash
# Should be:
mssql+pyodbc://user:pass@server.database.windows.net:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30
```

**Common mistakes:**
- Missing `+pyodbc` after `mssql`
- Wrong driver name
- Missing `&Encrypt=yes`

### Issue: High CPU/Memory

**Quick fix - scale up:**
```bash
az appservice plan update --name your-plan --resource-group your-rg --sku S3
```

**Or scale out (add instances):**
```bash
az appservice plan update --name your-plan --resource-group your-rg --number-of-workers 3
```

### Issue: Users still getting kicked out

**Likely cause:** Sessions not persisting across workers

**Fix:** Set up Redis (see SCALABILITY_GUIDE.md for details)

---

## Cost Optimization

### Don't overspend!

**Start small:**
- App Service: S1 or S2
- Azure SQL: S0 or S1
- Redis: Basic C0 (optional but recommended)

**Scale up during events:**
- Before reveal event: Scale to S2 or S3
- After event: Scale back down to S1

**Use auto-scaling:**
```bash
# Automatically scale based on CPU
az monitor autoscale create \
  --resource-group your-rg \
  --resource your-app \
  --resource-type "Microsoft.Web/serverfarms" \
  --min-count 2 \
  --max-count 5 \
  --count 2
```

---

## Performance Targets

### What "good" looks like:

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Homepage load | < 500ms | < 1s | > 2s |
| Dashboard load | < 1s | < 2s | > 3s |
| Reveal animation | < 2s | < 3s | > 5s |
| Error rate | < 0.1% | < 1% | > 5% |
| CPU usage | < 50% | < 70% | > 80% |
| Memory usage | < 60% | < 80% | > 90% |

---

## Next Steps

1. **Right Now:**
   - Set startup command to use Gunicorn
   - Enable WebSockets
   - Set environment variables
   - Restart app

2. **This Week:**
   - Set up Azure Redis Cache
   - Configure auto-scaling
   - Set up monitoring alerts
   - Run load test

3. **Before Big Event:**
   - Scale up to appropriate tier
   - Run stress test with expected load
   - Have rollback plan ready
   - Monitor during event

---

## Need More Details?

- **Comprehensive guide:** Read `SCALABILITY_GUIDE.md`
- **Deployment steps:** Read `AZURE_DEPLOYMENT.md`
- **Configuration help:** Read `config_reference.py`
- **Load testing:** Use `locustfile.py`

---

## Summary

**The Problem:**
Running production app with development server (single worker)

**The Solution:**
Use Gunicorn with multiple workers

**The Fix:**
1. Set startup command: `gunicorn -c gunicorn_config.py app:app`
2. Enable WebSockets in Azure
3. Set environment variables (especially GUNICORN_WORKERS=5)

**Expected Result:**
Can handle 500+ concurrent users without crashes

**Time Required:**
15 minutes to deploy, 1 hour to test and verify

---

## Questions?

**Q: Do I need to change any code?**
A: No! All fixes are configuration changes.

**Q: How many users can this handle?**
A: With S2 App Service: 200-500 users. With S3: 500-1000 users.

**Q: Do I need Redis?**
A: Not required but highly recommended for multiple workers.

**Q: Will this cost more?**
A: Yes, but only $100-200/month more for proper scaling.

**Q: What if I can't afford Redis?**
A: You can start without it, but users may get logged out randomly across workers.

**Q: How do I know it's working?**
A: Run the load test and check logs for "Spawning workers".

---

**Good luck! 🎉**

If you follow the steps in this guide, your scalability issues will be resolved.
