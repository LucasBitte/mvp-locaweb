targetScope = 'resourceGroup'
param registryName string
param location string

resource registry 'Microsoft.MachineLearningServices/registries@2024-04-01' = {
  name: registryName
  location: location
  kind: 'registry'
  identity: { type: 'SystemAssigned' }
  tags: {
    project: 'mvp-locaweb'
    purpose: 'model-registry'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    regionDetails: [
      {
        location: location
        acrDetails: [
          {
            systemCreatedAcrAccount: {
              acrAccountSku: 'Basic'
              acrAccountName: 'acr${uniqueString(resourceGroup().id, registryName, location)}'
            }
          }
        ]
        storageAccountDetails: [
          {
            systemCreatedStorageAccount: {
              storageAccountType: 'Standard_LRS'
              storageAccountName: 'st${uniqueString(resourceGroup().id, registryName, location)}'
              storageAccountHnsEnabled: false
              allowBlobPublicAccess: false
            }
          }
        ]
      }
    ]
  }
}

output registryId string = registry.id
