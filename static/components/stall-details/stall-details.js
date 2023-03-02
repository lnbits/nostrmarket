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
      mapStall: function (stall) {
        stall.shipping_zones.forEach(
          z =>
            (z.label = z.name
              ? `${z.name} (${z.countries.join(', ')})`
              : z.countries.join(', '))
        )
        return stall
      },
      getStall: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.inkey
          )
          this.stall = this.mapStall(data)

          console.log('### this.stall', this.stall)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      updateStall: async function () {
        try {
          const {data} = await LNbits.api.request(
            'PUT',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.adminkey,
            this.stall
          )
          this.stall = this.mapStall(data)
          this.$emit('stall-updated', this.stall)
          this.$q.notify({
            type: 'positive',
            message: 'Stall Updated',
            timeout: 5000
          })
        } catch (error) {
          console.warn(error)
          LNbits.utils.notifyApiError(error)
        }
      },
      deleteStall: function () {
        LNbits.utils
          .confirmDialog(
            `
             Products and orders will be deleted also!
             Are you sure you want to delete this stall?
            `
          )
          .onOk(async () => {
            try {
              await LNbits.api.request(
                'DELETE',
                '/nostrmarket/api/v1/stall/' + this.stallId,
                this.adminkey
              )
              this.$emit('stall-deleted', this.stallId)
              this.$q.notify({
                type: 'positive',
                message: 'Stall Deleted',
                timeout: 5000
              })
            } catch (error) {
              console.warn(error)
              LNbits.utils.notifyApiError(error)
            }
          })
      }
    },
    created: async function () {
      await this.getStall()
    }
  })
}
