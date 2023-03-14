async function merchantDetails(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('merchant-details', {
    name: 'merchant-details',
    props: ['merchant-id', 'adminkey', 'inkey'],
    template,

    data: function () {
      return {
        showKeys: false
      }
    },
    methods: {
      toggleMerchantKeys: async function () {
        this.showKeys = !this.showKeys
        this.$emit('show-keys', this.showKeys)
      },
      deleteMerchant: function () {
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
      }
    },
    created: async function () {}
  })
}
