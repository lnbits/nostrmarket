window.app.component('stall-list', {
  name: 'stall-list',
  template: '#stall-list',
  delimiters: ['${', '}'],
  props: [`adminkey`, 'inkey', 'wallet-options'],
  data: function () {
    return {
      filter: '',
      stalls: [],
      pendingStalls: [],
      currencies: [],
      stallDialog: {
        show: false,
        showRestore: false,
        data: {
          name: '',
          description: '',
          wallet: null,
          currency: 'sat',
          shippingZones: []
        }
      },
      zoneOptions: [],
      stallsTable: {
        columns: [
          {
            name: '',
            align: 'left',
            label: '',
            field: ''
          },
          {
            name: 'id',
            align: 'left',
            label: 'Name',
            field: 'id'
          },
          {
            name: 'currency',
            align: 'left',
            label: 'Currency',
            field: 'currency'
          },
          {
            name: 'description',
            align: 'left',
            label: 'Description',
            field: 'description'
          },
          {
            name: 'shippingZones',
            align: 'left',
            label: 'Shipping Zones',
            field: 'shippingZones'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      }
    }
  },
  computed: {
    filteredZoneOptions: function () {
      return this.zoneOptions.filter(
        z => z.currency === this.stallDialog.data.currency
      )
    }
  },
  methods: {
    sendStallFormData: async function () {
      const stallData = {
        name: this.stallDialog.data.name,
        wallet: this.stallDialog.data.wallet,
        currency: this.stallDialog.data.currency,
        shipping_zones: this.stallDialog.data.shippingZones,
        config: {
          description: this.stallDialog.data.description
        }
      }
      if (this.stallDialog.data.id) {
        stallData.id = this.stallDialog.data.id
        await this.restoreStall(stallData)
      } else {
        await this.createStall(stallData)
      }
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
        data.expanded = false
        this.stalls.unshift(data)
        this.$q.notify({
          type: 'positive',
          message: 'Stall created!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    restoreStall: async function (stallData) {
      try {
        stallData.pending = false
        const {data} = await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/stall/${stallData.id}`,
          this.adminkey,
          stallData
        )
        this.stallDialog.show = false
        data.expanded = false
        this.stalls.unshift(data)
        this.$q.notify({
          type: 'positive',
          message: 'Stall restored!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    deleteStall: async function (pendingStall) {
      LNbits.utils
        .confirmDialog(
          `
           Are you sure you want to delete this pending stall '${pendingStall.name}'?
          `
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              '/nostrmarket/api/v1/stall/' + pendingStall.id,
              this.adminkey
            )
            this.$q.notify({
              type: 'positive',
              message: 'Pending Stall Deleted',
              timeout: 5000
            })
          } catch (error) {
            console.warn(error)
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    getCurrencies: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/currencies',
          this.inkey
        )

        return ['sat', ...data]
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
      return []
    },
    getStalls: async function (pending = false) {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/nostrmarket/api/v1/stall?pending=${pending}`,
          this.inkey
        )
        return data.map(s => ({...s, expanded: false}))
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
      return []
    },
    getZones: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/zone',
          this.inkey
        )
        return data.map(z => ({
          ...z,
          label: z.name
            ? `${z.name} (${z.countries.join(', ')})`
            : z.countries.join(', ')
        }))
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
      return []
    },
    handleStallDeleted: function (stallId) {
      this.stalls = _.reject(this.stalls, function (obj) {
        return obj.id === stallId
      })
    },
    handleStallUpdated: function (stall) {
      const index = this.stalls.findIndex(r => r.id === stall.id)
      if (index !== -1) {
        stall.expanded = true
        this.stalls.splice(index, 1, stall)
      }
    },
    openCreateStallDialog: async function (stallData) {
      this.currencies = await this.getCurrencies()
      this.zoneOptions = await this.getZones()
      if (!this.zoneOptions || !this.zoneOptions.length) {
        this.$q.notify({
          type: 'warning',
          message: 'Please create a Shipping Zone first!'
        })
        return
      }
      this.stallDialog.data = stallData || {
        name: '',
        description: '',
        wallet: null,
        currency: 'sat',
        shippingZones: []
      }
      this.stallDialog.show = true
    },
    openSelectPendingStallDialog: async function () {
      this.stallDialog.showRestore = true
      this.pendingStalls = await this.getStalls(true)
    },
    openRestoreStallDialog: async function (pendingStall) {
      const shippingZonesIds = this.zoneOptions.map(z => z.id)
      await this.openCreateStallDialog({
        id: pendingStall.id,
        name: pendingStall.name,
        description: pendingStall.config?.description,
        currency: pendingStall.currency,
        shippingZones: (pendingStall.shipping_zones || [])
          .filter(z => shippingZonesIds.indexOf(z.id) !== -1)
          .map(z => ({
            ...z,
            label: z.name
              ? `${z.name} (${z.countries.join(', ')})`
              : z.countries.join(', ')
          }))
      })
    },
    customerSelectedForOrder: function (customerPubkey) {
      this.$emit('customer-selected-for-order', customerPubkey)
    },
    shortLabel(value = '') {
      if (value.length <= 64) return value
      return value.substring(0, 60) + '...'
    }
  },
  created: async function () {
    this.stalls = await this.getStalls()
    this.currencies = await this.getCurrencies()
    this.zoneOptions = await this.getZones()
  }
})
