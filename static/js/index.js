const merchant = async () => {
  Vue.component(VueQrcode.name, VueQrcode)

  await keyPair('static/components/key-pair/key-pair.html')
  await shippingZones('static/components/shipping-zones/shipping-zones.html')
  await stallDetails('static/components/stall-details/stall-details.html')
  await stallList('static/components/stall-list/stall-list.html')

  const nostr = window.NostrTools

  new Vue({
    el: '#vue',
    mixins: [windowMixin],
    data: function () {
      return {
        merchant: {},
        shippingZones: [],
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
        if (privateKey.toLowerCase().startsWith('nsec')) {
          privateKey = nostr.nip19.decode(privateKey)
        }
        await this.createMerchant(privateKey.data)
      },
      showImportKeysDialog: async function () {
        this.importKeyDialog.show = true
      },
      createMerchant: async function (privateKey) {
        const pubkey = nostr.getPublicKey(privateKey)
        const payload = {
          private_key: privateKey,
          public_key: pubkey,
          config: {}
        }
        try {
          const {data} = await LNbits.api.request(
            'POST',
            '/nostrmarket/api/v1/merchant',
            this.g.user.wallets[0].adminkey,
            payload
          )
          this.merchant = data
          this.$q.notify({
            type: 'positive',
            message: 'Keys generated!'
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
      }
    },
    created: async function () {
      console.log('### nostr', nostr)
      await this.getMerchant()
    }
  })
}

merchant()
