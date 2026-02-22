const nostr = window.NostrTools

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data: function () {
    return {
      activeTab: 'orders',
      selectedStallFilter: null,
      merchant: {},
      shippingZones: [],
      activeChatCustomer: '',
      orderPubkey: null,
      showKeys: false,
      stallCount: 0,
      importKeyDialog: {
        show: false,
        data: {
          privateKey: null
        }
      },
      generateKeyDialog: {
        show: false,
        privateKey: null,
        nsec: null,
        npub: null,
        showNsec: false
      },
      wsConnection: null,
      nostrStatus: {
        connected: false,
        error: null,
        relays_connected: 0,
        relays_total: 0
      }
    }
  },
  computed: {
    nostrStatusColor: function () {
      if (this.nostrStatus.connected) {
        return 'green'
      } else if (this.nostrStatus.warning) {
        return 'orange'
      }
      return 'red'
    },
    nostrStatusLabel: function () {
      return 'Connect'
    }
  },
  methods: {
    generateKeys: function () {
      const privateKey = nostr.generatePrivateKey()
      const publicKey = nostr.getPublicKey(privateKey)
      this.generateKeyDialog.privateKey = privateKey
      this.generateKeyDialog.nsec = nostr.nip19.nsecEncode(privateKey)
      this.generateKeyDialog.npub = nostr.nip19.npubEncode(publicKey)
      this.generateKeyDialog.showNsec = false
      this.generateKeyDialog.show = true
    },
    confirmGenerateKey: async function () {
      this.generateKeyDialog.show = false
      await this.createMerchant(this.generateKeyDialog.privateKey)
    },
    importKeys: async function () {
      this.importKeyDialog.show = false
      let privateKey = this.importKeyDialog.data.privateKey
      if (!privateKey) {
        return
      }
      try {
        if (privateKey.toLowerCase().startsWith('nsec')) {
          privateKey = nostr.nip19.decode(privateKey).data
        }
        // Check if this key is already in use
        const publicKey = nostr.getPublicKey(privateKey)
        if (this.merchant?.public_key === publicKey) {
          this.$q.notify({
            type: 'warning',
            message: 'This key is already your current profile'
          })
          return
        }
      } catch (error) {
        this.$q.notify({
          type: 'negative',
          message: `${error}`
        })
        return
      }
      await this.createMerchant(privateKey)
    },
    showImportKeysDialog: async function () {
      this.importKeyDialog.show = true
    },
    toggleShowKeys: function () {
      this.showKeys = !this.showKeys
    },
    toggleMerchantState: async function () {
      const merchant = await this.getMerchant()
      if (!merchant) {
        this.$q.notify({
          timeout: 5000,
          type: 'warning',
          message: 'Cannot fetch merchant!'
        })
        return
      }
      const message = merchant.config.active
        ? 'New orders will not be processed. Are you sure you want to deactivate?'
        : merchant.config.restore_in_progress
          ? 'Merchant restore  from nostr in progress. Please wait!! ' +
            'Activating now can lead to duplicate order processing. Click "OK" if you want to activate anyway?'
          : 'Are you sure you want activate this merchant?'

      LNbits.utils.confirmDialog(message).onOk(async () => {
        await this.toggleMerchant()
      })
    },
    toggleMerchant: async function () {
      try {
        const {data} = await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/merchant/${this.merchant.id}/toggle`,
          this.g.user.wallets[0].adminkey
        )
        const state = data.config.active ? 'activated' : 'disabled'
        this.merchant = data
        this.$q.notify({
          type: 'positive',
          message: `'Merchant ${state}`,
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    handleMerchantDeleted: function () {
      this.merchant = null
      this.shippingZones = []
      this.activeChatCustomer = ''
      this.showKeys = false
      this.stallCount = 0
    },
    createMerchant: async function (privateKey) {
      try {
        const pubkey = nostr.getPublicKey(privateKey)
        const payload = {
          private_key: privateKey,
          public_key: pubkey,
          config: {}
        }
        const {data} = await LNbits.api.request(
          'POST',
          '/nostrmarket/api/v1/merchant',
          this.g.user.wallets[0].adminkey,
          payload
        )
        this.merchant = data
        this.$q.notify({
          type: 'positive',
          message: 'Merchant Created!'
        })
        this.waitForNotifications()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getMerchant: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/merchant',
          this.g.user.wallets[0].inkey
        )
        this.merchant = data
        return data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    customerSelectedForOrder: function (customerPubkey) {
      this.activeChatCustomer = customerPubkey
    },
    filterOrdersForCustomer: function (customerPubkey) {
      this.orderPubkey = customerPubkey
    },
    showOrderDetails: async function (orderData) {
      await this.$refs.orderListRef.orderSelected(
        orderData.orderId,
        orderData.eventId
      )
    },
    waitForNotifications: async function () {
      if (!this.merchant) return
      try {
        const scheme = location.protocol === 'http:' ? 'ws' : 'wss'
        const port = location.port ? `:${location.port}` : ''
        const wsUrl = `${scheme}://${document.domain}${port}/api/v1/ws/${this.merchant.id}`
        console.log('Reconnecting to websocket: ', wsUrl)
        this.wsConnection = new WebSocket(wsUrl)
        this.wsConnection.onmessage = async e => {
          const data = JSON.parse(e.data)
          if (data.type === 'dm:0') {
            this.$q.notify({
              timeout: 5000,
              type: 'positive',
              message: 'New Order'
            })

            await this.$refs.directMessagesRef.handleNewMessage(data)
            return
          }
          if (data.type === 'dm:1') {
            await this.$refs.directMessagesRef.handleNewMessage(data)
            await this.$refs.orderListRef.addOrder(data)
            return
          }
          if (data.type === 'dm:2') {
            const orderStatus = JSON.parse(data.dm.message)
            this.$q.notify({
              timeout: 5000,
              type: 'positive',
              message: orderStatus.message
            })
            if (orderStatus.paid) {
              await this.$refs.orderListRef.orderPaid(orderStatus.id)
            }
            await this.$refs.directMessagesRef.handleNewMessage(data)
            return
          }
          if (data.type === 'dm:-1') {
            await this.$refs.directMessagesRef.handleNewMessage(data)
          }
          // order paid
          // order shipped
        }
      } catch (error) {
        this.$q.notify({
          timeout: 5000,
          type: 'warning',
          message: 'Failed to watch for updates',
          caption: `${error}`
        })
      }
    },
    checkNostrStatus: async function (showNotification = false) {
      try {
        const response = await fetch('/nostrclient/api/v1/relays')
        const body = await response.json()

        if (response.status === 200) {
          const relaysConnected = body.filter(r => r.connected).length
          if (body.length === 0) {
            this.nostrStatus = {
              connected: false,
              error: 'No relays configured in Nostr Client',
              relays_connected: 0,
              relays_total: 0,
              warning: true
            }
          } else {
            this.nostrStatus = {
              connected: true,
              error: null,
              relays_connected: relaysConnected,
              relays_total: body.length
            }
          }
        } else {
          this.nostrStatus = {
            connected: false,
            error: body.detail,
            relays_connected: 0,
            relays_total: 0
          }
        }

        if (showNotification) {
          this.$q.notify({
            timeout: 3000,
            type: this.nostrStatus.connected ? 'positive' : 'warning',
            message: this.nostrStatus.connected ? 'Connected' : 'Disconnected',
            caption: this.nostrStatus.error || undefined
          })
        }
      } catch (error) {
        console.error('Failed to check nostr status:', error)
        this.nostrStatus = {
          connected: false,
          error: error.message,
          relays_connected: 0,
          relays_total: 0
        }
        if (showNotification) {
          this.$q.notify({
            timeout: 5000,
            type: 'negative',
            message: this.nostrStatus.error
          })
        }
      }
    },
    restartNostrConnection: async function () {
      LNbits.utils
        .confirmDialog(
          'Are you sure you want to reconnect to the nostrclient extension?'
        )
        .onOk(async () => {
          try {
            this.$q.notify({
              timeout: 2000,
              type: 'info',
              message: 'Reconnecting...'
            })
            await LNbits.api.request(
              'PUT',
              '/nostrmarket/api/v1/restart',
              this.g.user.wallets[0].adminkey
            )
            // Check status after restart (give time for websocket to reconnect)
            setTimeout(() => this.checkNostrStatus(true), 3000)
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    publishNip15: async function () {
      try {
        const {data: stalls} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/stall?pending=false',
          this.g.user.wallets[0].inkey
        )
        for (const stall of stalls) {
          await LNbits.api.request(
            'PUT',
            `/nostrmarket/api/v1/stall/${stall.id}`,
            this.g.user.wallets[0].adminkey,
            stall
          )
        }
        // Fetch products from all stalls
        let productCount = 0
        for (const stall of stalls) {
          const {data: products} = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/stall/product/${stall.id}?pending=false`,
            this.g.user.wallets[0].inkey
          )
          for (const product of products) {
            await LNbits.api.request(
              'PATCH',
              `/nostrmarket/api/v1/product/${product.id}`,
              this.g.user.wallets[0].adminkey,
              product
            )
            productCount++
          }
        }
        this.$q.notify({
          type: 'positive',
          message: `Published ${stalls.length} stall(s) and ${productCount} product(s) to Nostr (NIP-15)`
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    refreshNip15: async function () {
      LNbits.utils
        .confirmDialog(
          'This will sync your stalls and products from Nostr relays. Continue?'
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'PUT',
              '/nostrmarket/api/v1/restart',
              this.g.user.wallets[0].adminkey
            )
            this.$q.notify({
              type: 'positive',
              message: 'Refreshing NIP-15 data from Nostr...'
            })
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    deleteNip15: async function () {
      LNbits.utils
        .confirmDialog(
          'WARNING: This will delete all your stalls and products from Nostr relays. This cannot be undone! Are you sure?'
        )
        .onOk(async () => {
          this.$q.notify({
            type: 'info',
            message: 'Delete NIP-15 from Nostr not yet implemented'
          })
        })
    },
    goToProducts: function (stallId) {
      this.selectedStallFilter = stallId
      this.activeTab = 'products'
    },
    goToOrders: function (stallId) {
      this.selectedStallFilter = stallId
    }
  },
  created: async function () {
    await this.getMerchant()
    this.activeTab = await window.determineActiveTab(this)
    await this.checkNostrStatus()
    setInterval(async () => {
      if (
        !this.wsConnection ||
        this.wsConnection.readyState !== WebSocket.OPEN
      ) {
        await this.waitForNotifications()
      }
    }, 1000)
  }
})
