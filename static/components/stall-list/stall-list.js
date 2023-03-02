async function stallList(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('stall-list', {
    name: 'stall-list',
    template,

    props: [`adminkey`, 'inkey', 'wallet-options'],
    data: function () {
      return {
        filter: '',
        stalls: [],
        currencies: [],
        stallDialog: {
          show: false,
          data: {
            name: '',
            wallet: null,
            currency: 'sat',
            shippingZones: []
          }
        },
        zoneOptions: []
      }
    },
    methods: {
      sendStallFormData: async function () {
        console.log('### sendStallFormData', this.stallDialog.data)

        await this.createStall({
          name: this.stallDialog.data.name,
          wallet: this.stallDialog.data.wallet,
          currency: this.stallDialog.data.currency,
          shipping_zones: this.stallDialog.data.shippingZones,
          config: {}
        })
      },
      createStall: async function (stall) {
        try {
          const {data} = await LNbits.api.request(
            'POST',
            '/nostrmarket/api/v1/stall',
            this.adminkey,
            stall
          )
          this.stallDialog.show = false
          this.$q.notify({
            type: 'positive',
            message: 'Stall created!'
          })
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      getCurrencies: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/currencies',
            this.inkey
          )

          this.currencies = ['sat', ...data]
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      getZones: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/zone',
            this.inkey
          )
          console.log('### zones', data)
          this.zoneOptions = data.map(z => ({
            ...z,
            label: z.name
              ? `${z.name} (${z.countries.join(', ')}})`
              : z.countries.join(', ')
          }))
          console.log('### this.zoneOptions', this.zoneOptions)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      openCreateStallDialog: async function () {
        await this.getCurrencies()
        await this.getZones()
        this.stallDialog.data = {
          name: '',
          wallet: null,
          currency: 'sat',
          shippingZones: []
        }
        this.stallDialog.show = true
      }
    },
    created: async function () {
      await this.getCurrencies()
      await this.getZones()
    }
  })
}
