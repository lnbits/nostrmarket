window.app.component('order-list', {
  name: 'order-list',
  props: ['stall-id', 'customer-pubkey-filter', 'adminkey', 'inkey'],
  template: '#order-list',
  delimiters: ['${', '}'],
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
      stalls: [],
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
      zoneOptions: [],
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
      const options = this.customers.map(c => ({
        label: this.buildCustomerLabel(c),
        value: c.public_key
      }))
      options.unshift({label: 'All', value: null, id: null})
      return options
    }
  },
  methods: {
    toShortId: function (value) {
      return value.substring(0, 5) + '...' + value.substring(value.length - 5)
    },
    formatDate: function (value) {
      return Quasar.date.formatDate(new Date(value * 1000), 'YYYY-MM-DD HH:mm')
    },
    satBtc(val, showUnit = true) {
      return satOrBtc(val, showUnit, true)
    },
    formatFiat(value, currency) {
      return Math.trunc(value) + ' ' + currency
    },
    shortLabel(value = '') {
      if (value.length <= 44) return value
      return value.substring(0, 20) + '...'
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
      const productCost = order.items.reduce((t, item) => {
        product = order.extra.products.find(p => p.id === item.product_id)
        return t + item.quantity * product.price
      }, 0)
      return productCost + order.extra.shipping_cost
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
    getOrder: async function (orderId) {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/nostrmarket/api/v1/order/${orderId}`,
          this.inkey
        )
        return {...data, expanded: false, isNew: true}
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    restoreOrder: async function (eventId) {
      console.log('### restoreOrder', eventId)
      try {
        this.search.restoring = true
        const {data} = await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/order/restore/${eventId}`,
          this.adminkey
        )
        await this.getOrders()
        this.$q.notify({
          type: 'positive',
          message: 'Order restored!'
        })
        return data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.search.restoring = false
      }
    },
    restoreOrders: async function () {
      try {
        this.search.restoring = true
        await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/orders/restore`,
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
    reissueOrderInvoice: async function (order) {
      try {
        const {data} = await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/order/reissue`,
          this.adminkey,
          {
            id: order.id,
            shipping_id: order.shipping_id
          }
        )
        this.$q.notify({
          type: 'positive',
          message: 'Order invoice reissued!'
        })
        data.expanded = order.expanded

        const i = this.orders.map(o => o.id).indexOf(order.id)
        if (i !== -1) {
          this.orders[i] = {...this.orders[i], ...data}
        }
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
    addOrder: async function (data) {
      if (
        !this.search.publicKey ||
        this.search.publicKey === data.customerPubkey
      ) {
        const orderData = JSON.parse(data.dm.message)
        const i = this.orders.map(o => o.id).indexOf(orderData.id)
        if (i === -1) {
          const order = await this.getOrder(orderData.id)
          this.orders.unshift(order)
        }
      }
    },
    orderSelected: async function (orderId, eventId) {
      const order = await this.getOrder(orderId)
      if (!order) {
        LNbits.utils
          .confirmDialog(
            'Order could not be found. Do you want to restore it from this direct message?'
          )
          .onOk(async () => {
            const restoredOrder = await this.restoreOrder(eventId)
            console.log('### restoredOrder', restoredOrder)
            if (restoredOrder) {
              restoredOrder.expanded = true
              restoredOrder.isNew = false
              this.orders = [restoredOrder]
            }
          })
        return
      }
      order.expanded = true
      order.isNew = false
      this.orders = [order]
    },
    getZones: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/zone',
          this.inkey
        )
        return data.map(z => ({
          id: z.id,
          value: z.id,
          label: z.name
            ? `${z.name} (${z.countries.join(', ')})`
            : z.countries.join(', ')
        }))
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
    getStallZones: function (stallId) {
      const stall = this.stalls.find(s => s.id === stallId)
      if (!stall) return []

      return this.zoneOptions.filter(z =>
        stall.shipping_zones.find(s => s.id === z.id)
      )
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
        const {data} = await LNbits.api.request(
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
    orderPaid: function (orderId) {
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
    this.zoneOptions = await this.getZones()
    this.stalls = await this.getStalls()
  }
})
