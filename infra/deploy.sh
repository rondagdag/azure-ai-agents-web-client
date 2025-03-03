#!/bin/bash

echo "Deploying the Azure resources..."

# Define resource group parameters
RG_NAME="rg-agent-as-a-svc"
RG_LOCATION="westus"
MODEL_NAME="gpt-4o"
AI_HUB_NAME="agent-wksp"
AI_PROJECT_NAME="agent-as-a-svc"
AI_PROJECT_FRIENDLY_NAME="Agent As A Service"
STORAGE_NAME="agentservicestorage"
AI_SERVICES_NAME="agent-svc"
MODEL_CAPACITY=140

# Create the resource group
az group create --name "$RG_NAME" --location "$RG_LOCATION"

# Deploy the Azure resources and save output to JSON
az deployment group create \
  --resource-group "$RG_NAME" \
  --template-file main.bicep \
  --parameters aiHubName="$AI_HUB_NAME" \
      aiProjectName="$AI_PROJECT_NAME" \
      aiProjectFriendlyName="$AI_PROJECT_FRIENDLY_NAME" \
      storageName="$STORAGE_NAME" \
      aiServicesName="$AI_SERVICES_NAME" \
      modelName="$MODEL_NAME" \
      modelCapacity="$MODEL_CAPACITY" \
      modelLocation="$RG_LOCATION" > output.json

# Parse the JSON file manually using grep and sed
if [ -f output.json ]; then
  AI_PROJECT_NAME=$(jq -r '.properties.outputs.aiProjectName.value' output.json)
  RESOURCE_GROUP_NAME=$(jq -r '.properties.outputs.resourceGroupName.value' output.json)
  SUBSCRIPTION_ID=$(jq -r '.properties.outputs.subscriptionId.value' output.json)

  # Run the Azure CLI command to get discovery_url
  DISCOVERY_URL=$(az ml workspace show -n "$AI_PROJECT_NAME" --resource-group "$RESOURCE_GROUP_NAME" --query discovery_url -o tsv)

  if [ -n "$DISCOVERY_URL" ]; then
    # Process the discovery_url to extract the HostName
    HOST_NAME=$(echo "$DISCOVERY_URL" | sed -e 's|^https://||' -e 's|/discovery$||')

    # Generate the AZURE_FOUNDRY_PROJECT_CONNSTRING
    AZURE_FOUNDRY_PROJECT_CONNSTRING="\"$HOST_NAME;$SUBSCRIPTION_ID;$RESOURCE_GROUP_NAME;$AI_PROJECT_NAME\""

    ENV_FILE_PATH="../src/workshop/.env"

    # Delete the file if it exists
    [ -f "$ENV_FILE_PATH" ] && rm "$ENV_FILE_PATH"

    # Write to the .env file
    {
      echo "AZURE_FOUNDRY_PROJECT_CONNSTRING=$AZURE_FOUNDRY_PROJECT_CONNSTRING"
      echo "AZURE_FOUNDRY_GPT_MODEL=\"$MODEL_NAME\""
    } > "$ENV_FILE_PATH"

    # Delete the output.json file
    rm -f output.json
  else
    echo "Error: discovery_url not found."
  fi
else
  echo "Error: output.json not found."
fi

# Set Variables
subId=$(az account show --query id --output tsv)
objectId=$(az ad signed-in-user show --query id -o tsv)

#Adding data scientist role
az role assignment create --role "f6c7c914-8db3-469d-8ca1-694a8f32e121" --assignee-object-id $objectId --scope /subscriptions/$subId/resourceGroups/$RG_NAME --assignee-principal-type 'User'
