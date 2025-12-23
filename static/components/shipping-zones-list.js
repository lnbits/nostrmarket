window.app.component('shipping-zones-list', {
  name: 'shipping-zones-list',
  props: ['adminkey', 'inkey'],
  template: '#shipping-zones-list',
  delimiters: ['${', '}'],
  data: function () {
    return {
      zones: [],
      filter: '',
      zoneDialog: {
        showDialog: false,
        data: {
          id: null,
          name: '',
          countries: [],
          cost: 0,
          currency: 'sat'
        }
      },
      currencies: [],
      shippingZoneOptions: [
        'Free (digital)',
        'Worldwide',
        'Europe',
        'Australia',
        'Austria',
        'Belgium',
        'Brazil',
        'Canada',
        'China',
        'Denmark',
        'Finland',
        'France',
        'Germany',
        'Greece',
        'Hong Kong',
        'Hungary',
        'Indonesia',
        'Ireland',
        'Israel',
        'Italy',
        'Japan',
        'Kazakhstan',
        'Korea',
        'Luxembourg',
        'Malaysia',
        'Mexico',
        'Netherlands',
        'New Zealand',
        'Norway',
        'Poland',
        'Portugal',
        'Romania',
        'Russia',
        'Saudi Arabia',
        'Singapore',
        'Spain',
        'Sweden',
        'Switzerland',
        'Thailand',
        'Turkey',
        'Ukraine',
        'United Kingdom',
        'United States',
        'Vietnam'
      ],
      zonesTable: {
        columns: [
          {
            name: 'name',
            align: 'left',
            label: 'Name',
            field: 'name',
            sortable: true
          },
          {
            name: 'countries',
            align: 'left',
            label: 'Countries',
            field: 'countries',
            sortable: true
          },
          {
            name: 'currency',
            align: 'left',
            label: 'Currency',
            field: 'currency',
            sortable: true
          },
          {
            name: 'cost',
            align: 'left',
            label: 'Cost',
            field: 'cost',
            sortable: true
          },
          {
            name: 'actions',
            align: 'right',
            label: 'Actions',
            field: ''
          }
        ],
        pagination: {
          rowsPerPage: 10,
          sortBy: 'name',
          descending: false
        }
      }
    }
  },
  methods: {
    openZoneDialog: function (data) {
      data = data || {
        id: null,
        name: '',
        countries: [],
        cost: 0,
        currency: 'sat'
      }
      this.zoneDialog.data = {...data}
      this.zoneDialog.showDialog = true
    },
    getZones: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/zone',
          this.inkey
        )
        this.zones = data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    sendZoneFormData: async function () {
      this.zoneDialog.showDialog = false
      if (this.zoneDialog.data.id) {
        await this.updateShippingZone(this.zoneDialog.data)
      } else {
        await this.createShippingZone(this.zoneDialog.data)
      }
      await this.getZones()
    },
    createShippingZone: async function (newZone) {
      try {
        await LNbits.api.request(
          'POST',
          '/nostrmarket/api/v1/zone',
          this.adminkey,
          newZone
        )
        this.$q.notify({
          type: 'positive',
          message: 'Zone created!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    updateShippingZone: async function (updatedZone) {
      try {
        await LNbits.api.request(
          'PATCH',
          `/nostrmarket/api/v1/zone/${updatedZone.id}`,
          this.adminkey,
          updatedZone
        )
        this.$q.notify({
          type: 'positive',
          message: 'Zone updated!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    confirmDeleteZone: function (zone) {
      LNbits.utils
        .confirmDialog(`Are you sure you want to delete zone "${zone.name}"?`)
        .onOk(async () => {
          await this.deleteShippingZone(zone.id)
        })
    },
    deleteShippingZone: async function (zoneId) {
      try {
        await LNbits.api.request(
          'DELETE',
          `/nostrmarket/api/v1/zone/${zoneId}`,
          this.adminkey
        )
        this.$q.notify({
          type: 'positive',
          message: 'Zone deleted!'
        })
        await this.getZones()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getCurrencies() {
      const currencies = window.g.allowedCurrencies || []
      this.currencies = ['sat', ...currencies]
    }
  },
  created: async function () {
    await this.getZones()
    this.getCurrencies()
  }
})
