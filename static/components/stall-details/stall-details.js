async function stallDetails(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('stall-details', {
    name: 'stall-details',
    template,

    props: [
      'stall-id',
      'adminkey',
      'inkey',
      'wallet-options',
      'zone-options',
      'currencies'
    ],
    data: function () {
      return {
        tab: 'info',
        stall: null
        // currencies: [],
      }
    },
    computed: {
      filteredZoneOptions: function () {
        if (!this.stall) return []
        return this.zoneOptions.filter(z => z.currency === this.stall.currency)
      }
    },
    methods: {
      getStall: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.inkey
          )
          this.stall = data
          console.log('### this.stall', this.stall)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      }

    },
    created: async function () {
      await this.getStall()
      console.log('### this.zoneOptions', this.zoneOptions)
    }
  })
}
