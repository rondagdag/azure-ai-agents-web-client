# Azure AI Agents Web Client

This project demonstrates the implementation of Azure AI Agent Service, a fully managed service for building, deploying, and scaling AI agents. It showcases how to simplify agent deployment, improve scalability, and extend functionality using Azure's cloud infrastructure.

## Documentation

- [Setup Guide](./docs/setup.md) - Detailed instructions for setting up the development environment and deploying the infrastructure
- [Agent as a Service Overview](./docs/article.md) - In-depth article about Agent as a Service (AaaS) and Azure AI Agent Service

## Project Overview

Azure AI Agent Service enables developers to:
- Build secure and scalable AI agents with minimal code
- Manage agent infrastructure automatically
- Integrate with Azure services seamlessly
- Deploy agents that can perform complex tasks autonomously

### Key Features

- Automatic tool calling and response handling
- Secure conversation state management
- Pre-built integrations with Azure services
- Simplified deployment process
- Enterprise-grade security and scaling

## Quick Start

1. Follow the [Setup Guide](./docs/getting-started/setup.md) to prepare your environment
2. Deploy the infrastructure using the provided scripts
3. Configure your environment variables
4. Run the sample agent application
```shell
> streamlit run AgentOnTheFly.py
```

## Infrastructure

The project uses Infrastructure as Code (IaC) with Bicep templates for deployment. Key components include:
- Azure AI Services
- Storage accounts
- Security configurations
- Networking setup

## Contributing

Feel free to submit issues and enhancement requests.
