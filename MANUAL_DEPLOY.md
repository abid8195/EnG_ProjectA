# Manual Azure Deployment Guide

## Prerequisites
- Azure App Service created: `qml-dataflow-studio-abid`
- Publish profile added to GitHub secrets

## Manual Deployment Steps

### 1. Update App Name (if different)
Edit `.github/workflows/azure-deploy.yml` line 9:
```yaml
AZURE_WEBAPP_NAME: your-actual-app-name
```

### 2. Commit Changes
```bash
git add .github/workflows/azure-deploy.yml
git commit -m "update: Set correct Azure app name"
git push origin feat/multidataset-qml
```

### 3. Trigger Deployment
Option A - Merge to main:
```bash
git checkout main
git merge feat/multidataset-qml
git push origin main
```

Option B - Direct push to main:
```bash
git checkout main
git pull origin main
git merge feat/multidataset-qml
git push origin main
```

### 4. Monitor Deployment
- Go to GitHub → Actions tab
- Watch "Deploy QML DataFlow Studio to Azure" workflow
- Should complete in 5-10 minutes

### 5. Test Deployment
Visit: `https://your-app-name.azurewebsites.net`

## Troubleshooting

### If GitHub Actions fails:
1. Check app name matches exactly in workflow
2. Verify publish profile secret is correct
3. Ensure Azure App Service exists

### If app doesn't start:
1. Check Azure Portal → App Service → Log stream
2. Verify Python version and startup command
3. Check Application Settings in Azure

### Quick Fix Commands:
```bash
# Reset startup command in Azure CLI
az webapp config set --resource-group qml-dataflow-rg --name your-app-name --startup-file "gunicorn --bind 0.0.0.0:8000 --timeout 120 backend.app:app"

# Check app status
az webapp show --resource-group qml-dataflow-rg --name your-app-name --query state
```