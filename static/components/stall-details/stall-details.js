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
          this.stall.shipping_zones.forEach(
            z =>
              (z.label = z.name
                ? `${z.name} (${z.countries.join(', ')})`
                : z.countries.join(', '))
          )
          console.log('### this.stall', this.stall)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      }
    },
    created: async function () {
      await this.getStall()
    }
  })
}
