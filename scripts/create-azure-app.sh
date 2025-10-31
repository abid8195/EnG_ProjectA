# Azure CLI Commands to Create App Service
# Run these commands in order after installing Azure CLI

# 1. Login to Azure
az login

# 2. Create resource group
az group create --name qml-dataflow-rg --location "East US"

# 3. Create App Service plan (Free tier)
az appservice plan create --name qml-dataflow-plan --resource-group qml-dataflow-rg --sku F1 --is-linux

# 4. Create web app with Python 3.11
az webapp create --resource-group qml-dataflow-rg --plan qml-dataflow-plan --name qml-dataflow-studio-abid --runtime "PYTHON|3.11"

# 5. Configure app settings
az webapp config appsettings set --resource-group qml-dataflow-rg --name qml-dataflow-studio-abid --settings PYTHONPATH="/home/site/wwwroot" FLASK_ENV="production" SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# 6. Set startup command
az webapp config set --resource-group qml-dataflow-rg --name qml-dataflow-studio-abid --startup-file "gunicorn --bind 0.0.0.0:8000 --timeout 120 backend.app:app"

echo "Azure App Service created successfully!"
echo "App URL: https://qml-dataflow-studio-abid.azurewebsites.net"