# Setup Guide

This guide will walk you through setting up and deploying the Azure AI Agent Service infrastructure.

## Prerequisites

1. **Azure Subscription**
   - An active Azure subscription
   - Permissions to create resources and assign roles

2. **Development Environment**
   - GitHub Codespaces or VSCode
   - Python 3.13 or higher
   - Azure CLI installed
   - Git
   
## Project Structure

```
.
├── infra/               # Infrastructure as Code (IaC)
│   ├── deploy.sh       # Deployment script
│   ├── main.bicep      # Main Bicep template
│   └── modules-basic-keys/
├── docs/               # Documentation
└── requirements.txt    # Python dependencies
```

## Step-by-Step Setup Instructions

### 1. Authentication Setup

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"

# Verify current subscription
az account show
```

### 2. Deploy Azure Resources

1. Clone the Repository
2. Set Environment Variables
3. Run Deployment Script

For detailed deployment instructions and configuration options, refer to our [deployment guide](deployment.md).

## Troubleshooting

### Common Issues

1. **Deployment Failures**
   - Ensure you have sufficient permissions
   - Check if the region supports all required services
   - Verify resource name availability

2. **Authentication Issues**
   - Re-run `az login`
   - Check your subscription status
   - Verify role assignments

3. **Python Dependencies**
   - Update pip: `python -m pip install --upgrade pip`
   - Clear pip cache if needed: `pip cache purge`
   - Install individual packages if bulk install fails

## Next Steps

After successful setup:

1. Review the architecture documentation
2. Try the sample applications
3. Explore the API documentation
4. Start building your own AI agents