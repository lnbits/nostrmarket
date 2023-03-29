const merchant = async () => {
  Vue.component(VueQrcode.name, VueQrcode)

  await keyPair('static/components/key-pair/key-pair.html')
  await shippingZones('static/components/shipping-zones/shipping-zones.html')
  await stallDetails('static/components/stall-details/stall-details.html')
  await stallList('static/components/stall-list/stall-list.html')
  await orderList('static/components/order-list/order-list.html')
  await directMessages('static/components/direct-messages/direct-messages.html')
  await merchantDetails(
    'static/components/merchant-details/merchant-details.html'
  )

  const nostr = window.NostrTools

  new Vue({
    el: '#vue',
    mixins: [windowMixin],
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
        }
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
      toggleMerchantKeys: function (value) {
        this.showKeys = value
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
      waitForNotifications: async function () {
        try {
          const scheme = location.protocol === 'http:' ? 'ws' : 'wss'
          const port = location.port ? `:${location.port}` : ''
          const wsUrl = `${scheme}://${document.domain}${port}/api/v1/ws/${this.merchant.id}`
          const wsConnection = new WebSocket(wsUrl)
          console.log('### waiting for events')
          wsConnection.onmessage = async e => {
            console.log('### e', e)
            const data = JSON.parse(e.data)
            if (data.type === 'new-order') {
              this.$q.notify({
                timeout: 5000,
                type: 'positive',
                message: 'New Order'
              })
              await this.$refs.orderListRef.addOrder(data)
            } else if (data.type === 'new-customer') {
            } else if (data.type === 'new-direct-message') {
            }
          }
        } catch (error) {
          this.$q.notify({
            timeout: 5000,
            type: 'warning',
            message: 'Failed to watch for updated',
            caption: `${error}`
          })
        }
      }
    },
    created: async function () {
      await this.getMerchant()
      await this.waitForNotifications()
    }
  })
}

merchant()
