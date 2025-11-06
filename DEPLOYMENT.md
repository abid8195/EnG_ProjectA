# 🚀 QML DataFlow Studio - Azure Deployment Guide

This guide helps you deploy your QML DataFlow Studio to Azure App Service using GitHub Actions.

## 📋 Prerequisites

1. **Azure Account**: Sign up at [azure.microsoft.com](https://azure.microsoft.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Azure CLI** (optional): For command-line deployment

## 🔧 Step 1: Create Azure App Service

### Option A: Using Azure Portal (Recommended)

1. **Login to Azure Portal**: Go to [portal.azure.com](https://portal.azure.com)

2. **Create App Service**:
   - Click "Create a resource"
   - Search for "Web App"
   - Click "Create"

3. **Configure Basic Settings**:
   ```
   Subscription: Your subscription
   Resource Group: Create new "qml-dataflow-rg"
   Name: qml-dataflow-studio (or your preferred name)
   Publish: Code
   Runtime Stack: Python 3.11
   Operating System: Linux
   Region: East US (or closest to you)
   ```

4. **Configure App Service Plan**:
   - Create new plan
   - Pricing tier: F1 (Free) for testing, B1 (Basic) for production

5. **Review and Create**: Click "Review + create" then "Create"

### Option B: Using Azure CLI

```bash
# Login to Azure
az login

# Create resource group
az group create --name qml-dataflow-rg --location "East US"

# Create App Service plan
az appservice plan create --name qml-dataflow-plan --resource-group qml-dataflow-rg --sku F1 --is-linux

# Create web app
az webapp create --resource-group qml-dataflow-rg --plan qml-dataflow-plan --name qml-dataflow-studio --runtime "PYTHON|3.11"
```

## 🔑 Step 2: Set Up GitHub Actions Secrets

1. **Get Publish Profile**:
   - In Azure Portal, go to your App Service
   - Click "Get publish profile"
   - Download the `.PublishSettings` file
   - Open it and copy all the content

2. **Add GitHub Secret**:
   - Go to your GitHub repository
   - Click "Settings" → "Secrets and variables" → "Actions"
   - Click "New repository secret"
   - Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Value: Paste the entire publish profile content
   - Click "Add secret"

## 🚀 Step 3: Deploy Using GitHub Actions

1. **Commit and Push**:
   ```bash
   git add .
   git commit -m "feat: Add Azure deployment configuration"
   git push origin feat/multidataset-qml
   ```

2. **Monitor Deployment**:
   - Go to GitHub repository → "Actions" tab
   - Watch the deployment progress
   - The workflow will:
     - Build and test your application
     - Deploy to Azure App Service

3. **Access Your App**:
   - Once deployment completes, visit: `https://qml-dataflow-studio.azurewebsites.net`
   - (Replace with your actual app name)

## 🔧 Step 4: Configure Azure App Service Settings

1. **Set Environment Variables**:
   - In Azure Portal, go to your App Service
   - Click "Configuration" → "Application settings"
   - Add these settings:
     ```
     PYTHONPATH = /home/site/wwwroot
     FLASK_APP = backend/app.py
     FLASK_ENV = production
     SCM_DO_BUILD_DURING_DEPLOYMENT = true
     ```

2. **Configure Startup Command**:
   - In Configuration → "General settings"
   - Startup Command: `bash startup.sh`

## 🎯 Step 5: Test Your Deployment

1. **Health Check**: Visit `https://your-app-name.azurewebsites.net/health`
2. **Main App**: Visit `https://your-app-name.azurewebsites.net`
3. **Test Features**:
   - Load predefined datasets (Diabetes, Iris, Real Estate)
   - Create nodes and connect them
   - Run QML pipeline

## 🔍 Troubleshooting

### Common Issues

1. **Deployment Fails**:
   - Check GitHub Actions logs
   - Verify publish profile secret
   - Ensure all required files are committed

2. **App Doesn't Start**:
   - Check Azure App Service logs
   - Verify Python version compatibility
   - Check startup command configuration

3. **Import Errors**:
   - Verify all dependencies in `requirements.txt`
   - Check Python path configuration

### Viewing Logs

```bash
# Azure CLI method
az webapp log tail --name qml-dataflow-studio --resource-group qml-dataflow-rg

# Or in Azure Portal:
# App Service → Monitoring → Log stream
```

## 🔄 Continuous Deployment

The GitHub Actions workflow automatically deploys when you:
- Push to `main` or `feat/multidataset-qml` branches
- Create pull requests to `main`

## 💡 Production Considerations

1. **Scaling**: Upgrade to higher pricing tiers for better performance
2. **Custom Domain**: Add your own domain in Azure Portal
3. **SSL Certificate**: Enable HTTPS with free Azure certificates
4. **Monitoring**: Set up Application Insights for monitoring
5. **Backup**: Configure backup schedules for your app

## 📊 Cost Estimation

- **Free Tier (F1)**: $0/month (limited compute, 60 minutes/day)
- **Basic Tier (B1)**: ~$13/month (better performance, always-on)
- **Standard Tier (S1)**: ~$56/month (production-ready, auto-scaling)

## 🎉 Next Steps

After successful deployment:
1. Share your app URL with users
2. Monitor usage and performance
3. Set up custom domain (optional)
4. Configure Application Insights for analytics
5. Set up Azure DevOps for advanced CI/CD (optional)

Your QML DataFlow Studio is now live and accessible to the world! 🌍✨