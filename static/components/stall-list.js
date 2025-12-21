window.app.component('stall-list', {
  name: 'stall-list',
  template: '#stall-list',
  delimiters: ['${', '}'],
  props: ['adminkey', 'inkey', 'wallet-options'],
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
      editDialog: {
        show: false,
        data: {
          id: '',
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
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {name: 'currency', align: 'left', label: 'Currency', field: 'currency'},
          {name: 'description', align: 'left', label: 'Description', field: row => row.config?.description || ''},
          {name: 'shippingZones', align: 'left', label: 'Shipping Zones', field: row => row.shipping_zones?.map(z => z.name).join(', ') || ''},
          {name: 'actions', align: 'right', label: 'Actions', field: ''}
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
    },
    editFilteredZoneOptions: function () {
      return this.zoneOptions.filter(
        z => z.currency === this.editDialog.data.currency
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
        this.stalls.unshift(data)
        this.$q.notify({
          type: 'positive',
          message: 'Stall restored!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    updateStall: async function () {
      try {
        const stallData = {
          id: this.editDialog.data.id,
          name: this.editDialog.data.name,
          wallet: this.editDialog.data.wallet,
          currency: this.editDialog.data.currency,
          shipping_zones: this.editDialog.data.shippingZones,
          config: {
            description: this.editDialog.data.description
          }
        }
        const {data} = await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/stall/${stallData.id}`,
          this.adminkey,
          stallData
        )
        this.editDialog.show = false
        const index = this.stalls.findIndex(s => s.id === data.id)
        if (index !== -1) {
          this.stalls.splice(index, 1, data)
        }
        this.$q.notify({
          type: 'positive',
          message: 'Stall updated!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    deleteStall: async function (stall) {
      try {
        await LNbits.api.request(
          'DELETE',
          '/nostrmarket/api/v1/stall/' + stall.id,
          this.adminkey
        )
        this.stalls = this.stalls.filter(s => s.id !== stall.id)
        this.pendingStalls = this.pendingStalls.filter(s => s.id !== stall.id)
        this.$q.notify({
          type: 'positive',
          message: 'Stall deleted'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    confirmDeleteStall: function (stall) {
      LNbits.utils
        .confirmDialog(
          `Products and orders will be deleted also! Are you sure you want to delete stall "${stall.name}"?`
        )
        .onOk(async () => {
          await this.deleteStall(stall)
        })
    },
    getCurrencies: function () {
      const currencies = window.g.allowedCurrencies || []
      return ['sat', ...currencies]
    },
    getStalls: async function (pending = false) {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/nostrmarket/api/v1/stall?pending=${pending}`,
          this.inkey
        )
        return data
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
    openCreateStallDialog: async function (stallData) {
      this.currencies = this.getCurrencies()
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
    openEditStallDialog: async function (stall) {
      this.currencies = this.getCurrencies()
      this.zoneOptions = await this.getZones()
      this.editDialog.data = {
        id: stall.id,
        name: stall.name,
        description: stall.config?.description || '',
        wallet: stall.wallet,
        currency: stall.currency,
        shippingZones: (stall.shipping_zones || []).map(z => ({
          ...z,
          label: z.name
            ? `${z.name} (${z.countries.join(', ')})`
            : z.countries.join(', ')
        }))
      }
      this.editDialog.show = true
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
    goToProducts: function (stall) {
      this.$emit('go-to-products', stall.id)
    },
    goToOrders: function (stall) {
      this.$emit('go-to-orders', stall.id)
    },
    shortLabel(value = '') {
      if (value.length <= 64) return value
      return value.substring(0, 60) + '...'
    }
  },
  created: async function () {
    this.stalls = await this.getStalls()
    this.currencies = this.getCurrencies()
    this.zoneOptions = await this.getZones()
  }
})
