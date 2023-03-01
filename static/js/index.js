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
        showKeys: false
      }
    },
    methods: {
      generateKeys: async function () {
        const privkey = nostr.generatePrivateKey()
        const pubkey = nostr.getPublicKey(privkey)

        const payload = {private_key: privkey, public_key: pubkey, config: {}}
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
      await this.getMerchant()
    }
  })
}

merchant()
