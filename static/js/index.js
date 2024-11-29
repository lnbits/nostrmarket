const nostr = window.NostrTools

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data: function () {
    return {
      merchant: {},
      shippingZones: [],
      activeChatCustomer: '',
      orderPubkey: null,
      showKeys: false,
      importKeyDialog: {
        show: false,
        data: {
          privateKey: null
        }
      },
      wsConnection: null
    }
  },
  methods: {
    generateKeys: async function () {
      const privateKey = nostr.generatePrivateKey()
      await this.createMerchant(privateKey)
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
      } catch (error) {
        this.$q.notify({
          type: 'negative',
          message: `${error}`
        })
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
    restartNostrConnection: async function () {
      LNbits.utils
        .confirmDialog(
          'Are you sure you want to reconnect to the nostrcient extension?'
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'PUT',
              '/nostrmarket/api/v1/restart',
              this.g.user.wallets[0].adminkey
            )
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    }
  },
  created: async function () {
    await this.getMerchant()
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
