const merchant = async () => {
  Vue.component(VueQrcode.name, VueQrcode)

  await stallDetails('static/components/stall-details/stall-details.html')
  await keyPair('static/components/key-pair/key-pair.html')

  const nostr = window.NostrTools

  new Vue({
    el: '#vue',
    mixins: [windowMixin],
    data: function () {
      return {
        merchant: {},
        showKeys: false
      }
    },
    methods: {
      generateKeys: async function () {
        const privkey = nostr.generatePrivateKey()
        const pubkey = nostr.getPublicKey(privkey)

        const data = {private_key: privkey, public_key: pubkey, config: {}}
        try {
          await LNbits.api.request(
            'POST',
            '/nostrmarket/api/v1/merchant',
            this.g.user.wallets[0].adminkey,
            data
          )
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      getMerchant: async function () {
        try {
          const {data} = await LNbits.api.request(
            'get',
            '/nostrmarket/api/v1/merchant',
            this.g.user.wallets[0].adminkey
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
