async function orderList(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('order-list', {
    name: 'order-list',
    props: ['stall-id', 'customer-pubkey-filter', 'adminkey', 'inkey'],
    template,

    watch: {
      customerPubkeyFilter: async function (n) {
        this.search.publicKey = n
        this.search.isPaid = {label: 'All', id: null}
        this.search.isShipped = {label: 'All', id: null}
        await this.getOrders()
      }
    },

    data: function () {
      return {
        orders: [],
        selectedOrder: null,
        shippingMessage: '',
        showShipDialog: false,
        filter: '',
        search: {
          publicKey: '',
          isPaid: {
            label: 'All',
            id: null
          },
          isShipped: {
            label: 'All',
            id: null
          }
        },
        customers: [],
        ternaryOptions: [
          {
            label: 'All',
            id: null
          },
          {
            label: 'Yes',
            id: 'true'
          },
          {
            label: 'No',
            id: 'false'
          }
        ],
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
              label: 'Order ID',
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
              name: 'public_key',
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
            ? `stall/order/${this.stallId}`
            : 'order'

          const query = []
          if (this.search.publicKey) {
            query.push(`pubkey=${this.search.publicKey}`)
          }
          if (this.search.isPaid.id) {
            query.push(`paid=${this.search.isPaid.id}`)
          }
          if (this.search.isShipped.id) {
            query.push(`shipped=${this.search.isShipped.id}`)
          }
          const {data} = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/${ordersPath}?${query.join('&')}`,
            this.inkey
          )
          this.orders = data.map(s => ({...s, expanded: false}))
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      updateOrderShipped: async function () {
        this.selectedOrder.shipped = !this.selectedOrder.shipped
        try {
          await LNbits.api.request(
            'PATCH',
            `/nostrmarket/api/v1/order/${this.selectedOrder.id}`,
            this.adminkey,
            {
              id: this.selectedOrder.id,
              message: this.shippingMessage,
              shipped: this.selectedOrder.shipped
            }
          )
          this.$q.notify({
            type: 'positive',
            message: 'Order updated!'
          })
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
        this.showShipDialog = false
      },
      showShipOrderDialog: function (order) {
        this.selectedOrder = order
        this.shippingMessage = order.shipped
          ? `The order has been shipped! Order ID: '${order.id}' `
          : `The order has NOT yet been shipped! Order ID: '${order.id}'`

        // do not change the status yet
        this.selectedOrder.shipped = !order.shipped
        this.showShipDialog = true
      },
      customerSelected: function (customerPubkey) {
        this.$emit('customer-selected', customerPubkey)
      },
      getCustomers: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/customers',
            this.inkey
          )
          this.customers = data
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      buildCustomerLabel: function (c) {
        let label = `${c.profile.name || 'unknown'} ${c.profile.about || ''}`
        if (c.unread_messages) {
          label += `[new: ${c.unread_messages}]`
        }
        label += `  (${c.public_key.slice(0, 16)}...${c.public_key.slice(
          c.public_key.length - 16
        )}`
        return label
      }
    },
    created: async function () {
      if (this.stallId) {
        await this.getOrders()
      }
      await this.getCustomers()
    }
  })
}
