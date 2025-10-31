# 🚀 Azure App Service Setup Guide for QML DataFlow Studio

## Step 1: Create Azure App Service

### 1.1 Login to Azure Portal
- Go to [portal.azure.com](https://portal.azure.com)
- Sign in with your Microsoft account

### 1.2 Create Resource Group
1. Click "Resource groups" in the left menu
2. Click "+ Create"
3. Fill in:
   - **Subscription**: Your subscription
   - **Resource group name**: `qml-dataflow-rg`
   - **Region**: `East US` (or closest to you)
4. Click "Review + create" → "Create"

### 1.3 Create App Service
1. Click "Create a resource" (+ icon)
2. Search for "Web App" and select it
3. Click "Create"
4. Fill in **Basics** tab:
   ```
   Subscription: Your subscription
   Resource Group: qml-dataflow-rg (select existing)
   Name: qml-dataflow-studio-[yourname] (must be globally unique)
   Publish: Code
   Runtime stack: Python 3.11
   Operating System: Linux
   Region: East US (same as resource group)
   ```

5. **App Service Plan**:
   - Create new plan: `qml-dataflow-plan`
   - Pricing tier: Click "Change size"
     - For **testing**: Select "Dev/Test" → F1 (Free)
     - For **production**: Select "Production" → B1 (Basic)

6. Click "Review + create" → "Create"
7. Wait for deployment (2-3 minutes)

## Step 2: Configure App Service Settings

### 2.1 Basic Configuration
1. Go to your App Service: `qml-dataflow-studio-[yourname]`
2. In left menu, click "Configuration"
3. Click "General settings" tab
4. Set:
   ```
   Stack: Python
   Major version: 3.11
   Minor version: 3.11
   Startup Command: gunicorn --bind 0.0.0.0:8000 --timeout 120 backend.app:app
   ```
5. Click "Save"

### 2.2 Application Settings
1. Still in "Configuration", click "Application settings" tab
2. Click "+ New application setting" for each:

   **Setting 1:**
   ```
   Name: PYTHONPATH
   Value: /home/site/wwwroot
   ```

   **Setting 2:**
   ```
   Name: FLASK_ENV
   Value: production
   ```

   **Setting 3:**
   ```
   Name: SCM_DO_BUILD_DURING_DEPLOYMENT
   Value: true
   ```

3. Click "Save" at the top

## Step 3: Get Publish Profile for GitHub

### 3.1 Download Publish Profile
1. In your App Service overview page
2. Click "Get publish profile" (top toolbar)
3. Save the `.PublishSettings` file to your computer
4. Open the file with notepad/text editor
5. **Select ALL content** and copy it

### 3.2 Add to GitHub Secrets
1. Go to your GitHub repository: `https://github.com/abid8195/EnG_ProjectA`
2. Click "Settings" tab
3. In left menu: "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Fill in:
   ```
   Name: AZURE_WEBAPP_PUBLISH_PROFILE
   Secret: [paste the entire publish profile content here]
   ```
6. Click "Add secret"

## Step 4: Update Deployment Workflow

### 4.1 Update App Name in Workflow
1. In your VS Code, open `.github/workflows/azure-deploy.yml`
2. Change line 9:
   ```yaml
   AZURE_WEBAPP_NAME: qml-dataflow-studio-[yourname]  # Use your actual app name
   ```
3. Save the file

## Step 5: Deploy to Azure

### 5.1 Commit and Push
```bash
git add .github/workflows/azure-deploy.yml
git commit -m "update: Set Azure app name for deployment"
git push origin feat/multidataset-qml
```

### 5.2 Merge to Main Branch (Trigger Deployment)
```bash
git checkout main
git merge feat/multidataset-qml
git push origin main
```

### 5.3 Monitor Deployment
1. Go to GitHub → Actions tab
2. Watch the "Deploy QML DataFlow Studio to Azure" workflow
3. It should show green checkmarks when complete

## Step 6: Test Your Live App

### 6.1 Get Your App URL
- Your app will be available at: `https://qml-dataflow-studio-[yourname].azurewebsites.net`

### 6.2 Test Functionality
1. Visit the URL
2. Check health endpoint: `https://your-app.azurewebsites.net/health`
3. Test the three dataset buttons (Diabetes, Iris, Real Estate)
4. Create nodes and test connections
5. Try running a simple pipeline

## Step 7: Troubleshooting

### 7.1 View Azure Logs
1. In Azure Portal → Your App Service
2. Left menu: "Monitoring" → "Log stream"
3. Watch for any error messages

### 7.2 Common Issues and Fixes

**Issue: App shows "Application Error"**
- Check Application Settings are correct
- Verify startup command
- Check logs for Python import errors

**Issue: 500 Internal Server Error**
- Check if all dependencies installed
- Verify file paths in startup command
- Check Application Insights for detailed errors

**Issue: GitHub Action Fails**
- Verify publish profile secret is correct
- Check app name matches in workflow
- Ensure all files committed and pushed

### 7.3 Reset if Needed
If something goes wrong, you can:
1. Delete the App Service
2. Create a new one with different name
3. Update GitHub secrets with new publish profile

## 🎉 Success Checklist

- [ ] Azure App Service created
- [ ] Publish profile added to GitHub secrets
- [ ] GitHub Actions workflow updated with app name
- [ ] Code merged to main branch
- [ ] Deployment completed successfully
- [ ] App accessible at Azure URL
- [ ] Health endpoint returns OK
- [ ] Dataset buttons work
- [ ] Node creation and connection works

## 💰 Cost Monitoring

- **Free Tier (F1)**: $0/month - Good for testing
- **Basic Tier (B1)**: ~$13/month - Good for production
- Monitor costs in Azure Portal → Cost Management

---

**Your app will be live at**: `https://qml-dataflow-studio-[yourname].azurewebsites.net`

Follow these steps in order, and your QML DataFlow Studio will be deployed to Azure! 🌟