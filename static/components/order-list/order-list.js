async function orderList(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('order-list', {
    name: 'order-list',
    props: ['stall-id', 'customer-pubkey-filter', 'adminkey', 'inkey'],
    template,

    watch: {
      customerPubkeyFilter: async function (n) {
        this.search.publicKey = n
        this.search.isPaid = { label: 'All', id: null }
        this.search.isShipped = { label: 'All', id: null }
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
          publicKey: null,
          isPaid: {
            label: 'All',
            id: null
          },
          isShipped: {
            label: 'All',
            id: null
          },
          restoring: false
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
              label: 'Total Sats',
              field: 'total'
            },
            {
              name: 'fiat',
              align: 'left',
              label: 'Total Fiat',
              field: 'fiat'
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
              name: 'event_created_at',
              align: 'left',
              label: 'Created At',
              field: 'event_created_at'
            }
          ],
          pagination: {
            rowsPerPage: 10
          }
        }
      }
    },
    computed: {
      customerOptions: function () {
        const options = this.customers.map(c => ({ label: this.buildCustomerLabel(c), value: c.public_key }))
        options.unshift({ label: 'All', value: null, id: null })
        return options
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
      satBtc(val, showUnit = true) {
        return satOrBtc(val, showUnit, true)
      },
      formatFiat(value, currency) {
        return Math.trunc(value) + ' ' + currency
      },
      productName: function (order, productId) {
        product = order.extra.products.find(p => p.id === productId)
        if (product) {
          return product.name
        }
        return ''
      },
      productPrice: function (order, productId) {
        product = order.extra.products.find(p => p.id === productId)
        if (product) {
          return `${product.price} ${order.extra.currency}`
        }
        return ''
      },
      orderTotal: function (order) {
        return order.items.reduce((t, item) => {
          product = order.extra.products.find(p => p.id === item.product_id)
          return t + item.quantity * product.price
        }, 0)
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
          const { data } = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/${ordersPath}?${query.join('&')}`,
            this.inkey
          )
          this.orders = data.map(s => ({ ...s, expanded: false }))
          console.log("### this.orders", this.orders)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      getOrder: async function (orderId) {
        try {
          const { data } = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/order/${orderId}`,
            this.inkey
          )
          return { ...data, expanded: false, isNew: true }
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      restoreOrders: async function () {
        try {
          this.search.restoring = true
          await LNbits.api.request(
            'PUT',
            `/nostrmarket/api/v1/order/restore`,
            this.adminkey
          )
          await this.getOrders()
          this.$q.notify({
            type: 'positive',
            message: 'Orders restored!'
          })
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        } finally {
          this.search.restoring = false
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
      addOrder: async function (data) {
        if (
          !this.search.publicKey ||
          this.search.publicKey === data.customerPubkey
        ) {
          const order = await this.getOrder(data.orderId)
          this.orders.unshift(order)
        }
      },

      showShipOrderDialog: function (order) {
        this.selectedOrder = order
        this.shippingMessage = order.shipped
          ? 'The order has been shipped!'
          : 'The order has NOT yet been shipped!'

        // do not change the status yet
        this.selectedOrder.shipped = !order.shipped
        this.showShipDialog = true
      },
      customerSelected: function (customerPubkey) {
        this.$emit('customer-selected', customerPubkey)
      },
      getCustomers: async function () {
        try {
          const { data } = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/customer',
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
      },
      orderPaid: function(orderId) {
        const order = this.orders.find(o => o.id === orderId)
        if (order) {
          order.paid = true
        }
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
