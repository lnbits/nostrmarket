window.app.component('merchant-details', {
  name: 'merchant-details',
  template: '#merchant-details',
  props: ['merchant-id', 'adminkey', 'inkey', 'showKeys'],
  delimiters: ['${', '}'],
  data: function () {
    return {}
  },
  methods: {
    toggleShowKeys: async function () {
      this.$emit('toggle-show-keys')
    },

    republishMerchantData: async function () {
      try {
        await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/merchant/${this.merchantId}/nostr`,
          this.adminkey
        )
        this.$q.notify({
          type: 'positive',
          message: 'Merchant data republished to Nostr',
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    requeryMerchantData: async function () {
      try {
        await LNbits.api.request(
          'GET',
          `/nostrmarket/api/v1/merchant/${this.merchantId}/nostr`,
          this.adminkey
        )
        this.$q.notify({
          type: 'positive',
          message: 'Merchant data refreshed from Nostr',
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    deleteMerchantTables: function () {
      LNbits.utils
        .confirmDialog(
          `
             Stalls, products and orders will be deleted also!
             Are you sure you want to delete this merchant?
            `
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              '/nostrmarket/api/v1/merchant/' + this.merchantId,
              this.adminkey
            )
            this.$emit('merchant-deleted', this.merchantId)
            this.$q.notify({
              type: 'positive',
              message: 'Merchant Deleted',
              timeout: 5000
            })
          } catch (error) {
            console.warn(error)
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    deleteMerchantFromNostr: function () {
      LNbits.utils
        .confirmDialog(
          `
             Do you want to remove the merchant from Nostr?
            `
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              `/nostrmarket/api/v1/merchant/${this.merchantId}/nostr`,
              this.adminkey
            )
            this.$q.notify({
              type: 'positive',
              message: 'Merchant Deleted from Nostr',
              timeout: 5000
            })
          } catch (error) {
            console.warn(error)
            LNbits.utils.notifyApiError(error)
          }
        })
    }
  },
  created: async function () {}
})
