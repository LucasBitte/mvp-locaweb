targetScope = 'subscription'

@description('Assinatura escolhida explicitamente no arquivo local de configuração.')
param expectedSubscriptionId string
param resourceGroupName string
param registryName string
param location string
param alertEmail string
@minValue(1)
param monthlyBudget int
param budgetStart string
param budgetEnd string

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: '${registryName}-monthly'
  properties: {
    category: 'Cost'
    amount: monthlyBudget
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStart
      endDate: budgetEnd
    }
    // Escopo assinatura: também inclui os recursos do grupo gerenciado do AML.
    notifications: {
      actual80: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      actual100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: [alertEmail]
      }
      forecast100: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: [alertEmail]
      }
    }
  }
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'mvp-locaweb'
    purpose: 'model-registry'
  }
}

module registry './registry.bicep' = {
  name: 'locaweb-model-registry'
  scope: rg
  params: {
    registryName: registryName
    location: location
  }
  dependsOn: [budget]
}

output registryId string = registry.outputs.registryId
output configuredSubscriptionId string = expectedSubscriptionId
output deployedSubscriptionId string = subscription().subscriptionId
output budgetId string = budget.id
