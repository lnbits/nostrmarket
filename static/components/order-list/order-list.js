async function orderList(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('order-list', {
    name: 'order-list',
    props: ['stall-id', 'adminkey', 'inkey'],
    template,

    data: function () {
      return {
        orders: [],

        filter: '',
        ordersTable: {
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
              label: 'ID',
              field: 'id'
            },
            {
              name: 'total',
              align: 'left',
              label: 'Total',
              field: 'total'
            },
            {
              name: 'paid',
              align: 'left',
              label: 'Paid',
              field: 'paid'
            },
            {
              name: 'shipped',
              align: 'left',
              label: 'Shipped',
              field: 'shipped'
            },
            {
              name: 'pubkey',
              align: 'left',
              label: 'Customer',
              field: 'pubkey'
            },
            {
              name: 'time',
              align: 'left',
              label: 'Date',
              field: 'time'
            }
          ],
          pagination: {
            rowsPerPage: 10
          }
        }
      }
    },
    methods: {
      toShortId: function (value) {
        return value.substring(0, 5) + '...' + value.substring(value.length - 5)
      },
      formatDate: function (value) {
        return Quasar.utils.date.formatDate(
          new Date(value * 1000),
          'YYYY-MM-DD HH:mm'
        )
      },
      productOverview: function (order, productId) {
        product = order.extra.products.find(p => p.id === productId)
        if (product) {
          return `${product.name} (${product.price} ${order.extra.currency})`
        }
        return ''
      },
      getOrders: async function () {
        try {
          const ordersPath = this.stallId
            ? `/stall/order/${this.stallId}`
            : '/order'
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1' + ordersPath,
            this.inkey
          )
          this.orders = data.map(s => ({...s, expanded: false}))
          console.log('### this.orders', this.orders)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      }
    },
    created: async function () {
      await this.getOrders()
    }
  })
}
