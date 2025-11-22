# Quick Deployment Guide - Azure App Service

This is a quick reference for deploying the Secret Santa application to Azure App Service with proper scalability configurations.

## Prerequisites

- Azure subscription
- Azure CLI installed
- Application code ready to deploy

## Step 1: Create Azure Resources

### Option A: Using Azure CLI

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="secret-santa-rg"
LOCATION="eastus"
APP_NAME="secret-santa-app"
DB_SERVER="secret-santa-db"
DB_NAME="secretsanta"
REDIS_NAME="secret-santa-redis"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure SQL Server
az sql server create \
  --name $DB_SERVER \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --admin-user sqladmin \
  --admin-password 'YourStrongPassword123!'

# Create Azure SQL Database (S1 tier recommended for 200+ users)
az sql db create \
  --resource-group $RESOURCE_GROUP \
  --server $DB_SERVER \
  --name $DB_NAME \
  --service-objective S1

# Configure firewall to allow Azure services
az sql server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --server $DB_SERVER \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Create Azure Redis Cache (Basic tier minimum)
az redis create \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Create App Service Plan (S2 recommended for 200-500 users)
az appservice plan create \
  --name secret-santa-plan \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku S2 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan secret-santa-plan \
  --name $APP_NAME \
  --runtime "PYTHON:3.10"

# Enable Web Sockets (required for SocketIO)
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --web-sockets-enabled true
```

### Option B: Using Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Create Resource Group: `secret-santa-rg`
3. Create Azure SQL Database (S1 or higher)
4. Create Azure Redis Cache (Basic or Standard)
5. Create App Service (S2 or higher with Linux)
6. Enable Web Sockets in App Service Configuration

## Step 2: Configure Application Settings

Get connection strings first:

```bash
# Get SQL connection string
az sql db show-connection-string \
  --client ado.net \
  --server $DB_SERVER \
  --name $DB_NAME

# Get Redis connection string
az redis list-keys \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP
```

Set environment variables:

```bash
# Database connection
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    DATABASE_URL="mssql+pyodbc://sqladmin:YourStrongPassword123!@${DB_SERVER}.database.windows.net:1433/${DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"

# Redis connection
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    REDIS_URL="rediss://:YOUR_REDIS_KEY@${REDIS_NAME}.redis.cache.windows.net:6380/0"

# Gunicorn configuration
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    GUNICORN_WORKERS="5" \
    WORKER_CONNECTIONS="1000" \
    GUNICORN_TIMEOUT="120"

# Application configuration
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    SECRET_KEY="$(openssl rand -hex 32)" \
    SESSION_COOKIE_SECURE="true" \
    GIFT_BUDGET="1500"

# SMTP configuration (optional - can be set in app)
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    SMTP_HOST="smtp.office365.com" \
    SMTP_PORT="587" \
    SMTP_USER="noreply@yourcompany.com" \
    SMTP_PASSWORD="your-app-password" \
    SMTP_USE_TLS="true"
```

## Step 3: Configure Startup Command

```bash
az webapp config set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --startup-file "gunicorn -c gunicorn_config.py app:app"
```

Or set in Azure Portal:
1. Go to App Service → Configuration → General settings
2. Startup Command: `gunicorn -c gunicorn_config.py app:app`

## Step 4: Deploy Application

### Option A: Git Deployment

```bash
# Configure deployment source
az webapp deployment source config-local-git \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# Get Git URL
GIT_URL=$(az webapp deployment source show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query url --output tsv)

# Add remote and push
git remote add azure $GIT_URL
git push azure main
```

### Option B: ZIP Deployment

```bash
# Create deployment package
zip -r deploy.zip . -x "*.git*" "venv/*" "__pycache__/*" "*.pyc"

# Deploy
az webapp deployment source config-zip \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --src deploy.zip
```

### Option C: GitHub Actions

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

## Step 5: Configure Auto-Scaling (Recommended)

```bash
# Create auto-scale profile
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource $APP_NAME \
  --resource-type "Microsoft.Web/serverfarms" \
  --name secret-santa-autoscale \
  --min-count 2 \
  --max-count 10 \
  --count 2

# Scale out rule (when CPU > 70%)
az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name secret-santa-autoscale \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1

# Scale in rule (when CPU < 30%)
az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name secret-santa-autoscale \
  --condition "Percentage CPU < 30 avg 5m" \
  --scale in 1
```

## Step 6: Verify Deployment

```bash
# Check logs
az webapp log tail \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# Test health endpoint (after implementing)
curl https://${APP_NAME}.azurewebsites.net/health

# Open in browser
az webapp browse \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## Step 7: Set Up Monitoring

```bash
# Enable Application Insights
az monitor app-insights component create \
  --app ${APP_NAME}-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app ${APP_NAME}-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey --output tsv)

# Configure app to use Application Insights
az webapp config appsettings set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --settings \
    APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=${INSTRUMENTATION_KEY}"
```

## Step 8: Configure Alerts

```bash
# High CPU alert
az monitor metrics alert create \
  --name high-cpu-alert \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/{subscription-id}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_NAME} \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email your-email@company.com

# High memory alert
az monitor metrics alert create \
  --name high-memory-alert \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/{subscription-id}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_NAME} \
  --condition "avg MemoryPercentage > 85" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email your-email@company.com

# HTTP 5xx errors alert
az monitor metrics alert create \
  --name http-errors-alert \
  --resource-group $RESOURCE_GROUP \
  --scopes /subscriptions/{subscription-id}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_NAME} \
  --condition "total Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email your-email@company.com
```

## Recommended Resource Tiers by User Count

| Expected Users | App Service Plan | Azure SQL  | Redis Cache | Monthly Cost (est.) |
|----------------|------------------|------------|-------------|---------------------|
| 1-50           | B1               | Basic      | Basic C0    | ~$50                |
| 50-200         | S1               | S0         | Basic C0    | ~$150               |
| 200-500        | S2               | S1         | Standard C1 | ~$350               |
| 500-1000       | S3               | S2         | Standard C2 | ~$650               |
| 1000+          | P1V2             | S3+        | Standard C3 | ~$1000+             |

## Post-Deployment Checklist

- [ ] Application loads successfully
- [ ] Database connection works
- [ ] Redis connection works
- [ ] Web Sockets enabled
- [ ] SMTP emails send successfully
- [ ] Auto-scaling configured
- [ ] Monitoring and alerts set up
- [ ] HTTPS enforced
- [ ] Custom domain configured (optional)
- [ ] SSL certificate installed (optional)
- [ ] Backup policy configured
- [ ] Load testing performed

## Common Commands

```bash
# View logs in real-time
az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP

# Restart app
az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP

# Scale manually
az appservice plan update --name secret-santa-plan --resource-group $RESOURCE_GROUP --sku S3

# Update app settings
az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP --settings KEY=VALUE

# SSH into container (for debugging)
az webapp ssh --name $APP_NAME --resource-group $RESOURCE_GROUP

# Download logs
az webapp log download --name $APP_NAME --resource-group $RESOURCE_GROUP --log-file logs.zip
```

## Troubleshooting

### Issue: Application won't start

```bash
# Check logs
az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP

# Common fixes:
# 1. Verify startup command is correct
# 2. Check DATABASE_URL is properly formatted
# 3. Ensure all dependencies in requirements.txt
# 4. Verify Python version matches (3.10)
```

### Issue: Database connection fails

```bash
# Test connection string
# Check if firewall allows Azure services
az sql server firewall-rule list --server $DB_SERVER --resource-group $RESOURCE_GROUP

# Add your IP if testing locally
az sql server firewall-rule create \
  --server $DB_SERVER \
  --resource-group $RESOURCE_GROUP \
  --name MyIP \
  --start-ip-address YOUR_IP \
  --end-ip-address YOUR_IP
```

### Issue: WebSockets not working

```bash
# Verify WebSockets are enabled
az webapp config show --name $APP_NAME --resource-group $RESOURCE_GROUP --query webSocketsEnabled

# Enable if needed
az webapp config set --name $APP_NAME --resource-group $RESOURCE_GROUP --web-sockets-enabled true
```

### Issue: High CPU/Memory usage

```bash
# Check metrics
az monitor metrics list \
  --resource /subscriptions/{subscription-id}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Web/sites/${APP_NAME} \
  --metric "CpuPercentage,MemoryPercentage"

# Scale up
az appservice plan update --name secret-santa-plan --resource-group $RESOURCE_GROUP --sku S3

# Or scale out (more instances)
az appservice plan update --name secret-santa-plan --resource-group $RESOURCE_GROUP --number-of-workers 3
```

## Performance Testing

Before going live, test with expected load:

```bash
# Install locust
pip install locust

# Run load test
locust -f locustfile.py --host=https://${APP_NAME}.azurewebsites.net --users 100 --spawn-rate 10 --run-time 5m
```

Monitor during load test:
- CPU usage should stay < 80%
- Memory usage should stay < 85%
- Response times should stay < 2s
- No 500 errors

## Additional Resources

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Azure SQL Database Documentation](https://docs.microsoft.com/azure/sql-database/)
- [Azure Redis Cache Documentation](https://docs.microsoft.com/azure/redis-cache/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)

## Support

For issues:
1. Check Application Insights for errors
2. Review application logs
3. Verify all environment variables are set
4. Test database and Redis connections
5. Ensure Web Sockets are enabled

---

**Quick Deploy Command Summary:**

```bash
# After creating all resources and configuring settings:
git remote add azure <git-url-from-azure>
git push azure main

# Or using ZIP:
zip -r deploy.zip . -x "*.git*" "venv/*"
az webapp deployment source config-zip --name $APP_NAME --resource-group $RESOURCE_GROUP --src deploy.zip
```
