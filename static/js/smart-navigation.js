/**
 * Smart Tab Navigation
 * Determines the most relevant tab based on merchant setup status
 */

async function determineActiveTab(app) {
  // No merchant → Merchant tab
  if (!app.merchant || !app.merchant.id) {
    return 'merchant'
  }

  try {
    // Check for shipping zones
    const {data: zones} = await LNbits.api.request(
      'GET',
      '/nostrmarket/api/v1/zone',
      app.g.user.wallets[0].inkey
    )

    // Merchant but no zones → Shipping tab
    if (!zones || zones.length === 0) {
      app.$q.notify({
        timeout: 5000,
        type: 'info',
        message: 'Set up shipping zones to get started'
      })
      return 'shipping'
    }

    // Check for stalls
    const {data: stalls} = await LNbits.api.request(
      'GET',
      '/nostrmarket/api/v1/stall?pending=false',
      app.g.user.wallets[0].inkey
    )

    // Zones but no stalls → Stalls tab
    if (!stalls || stalls.length === 0) {
      app.$q.notify({
        timeout: 5000,
        type: 'info',
        message: 'Create a stall to start selling'
      })
      return 'stalls'
    }

    // Check for products across all stalls
    let hasProducts = false
    for (const stall of stalls) {
      const {data: products} = await LNbits.api.request(
        'GET',
        `/nostrmarket/api/v1/stall/product/${stall.id}?pending=false`,
        app.g.user.wallets[0].inkey
      )
      if (products && products.length > 0) {
        hasProducts = true
        break
      }
    }

    // Stalls but no products → Products tab
    if (!hasProducts) {
      app.$q.notify({
        timeout: 5000,
        type: 'info',
        message: 'Add products to your stall'
      })
      return 'products'
    }

    // Products exist → Orders tab
    return 'orders'
  } catch (error) {
    console.warn('Error determining active tab:', error)
    return 'merchant'
  }
}

window.determineActiveTab = determineActiveTab
