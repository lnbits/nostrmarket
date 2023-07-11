async function customerOrders(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-orders', {
    name: 'orders',
    template,

    props: ['orders', 'products', 'stalls', 'merchants'],
    data: function () {
      return {}
    },
    computed: {
      merchantOrders: function () {
        return Object.keys(this.orders).map(pubkey => ({ pubkey, orders: this.orders[pubkey].map(this.enrichOrder) }))
      }
    },
    methods: {
      enrichOrder: function (order) {
        return {
          ...order,
          stallName: this.stallNameForOrder(order),
          invoice: this.invoiceForOrder(order)
        }
      },
      stallNameForOrder: function (order) {
        try {
          console.log('### stallNameForOrder', order)
          const productId = order.items[0]?.product_id
          if (!productId) return 'Stall Name'
          const product = this.products.find(p => p.id === productId)
          if (!product) return 'Stall Name'
          const stall = this.stalls.find(s => s.id === product.stall_id)
          if (!stall) return 'Stall Name'
          return stall.name
        } catch (error) {
          return 'Stall Name'
        }

      },
      invoiceForOrder: function (order) {
        try {
          const lnPaymentOption = order?.payment_options?.find(p => p.type === 'ln')
          if (!lnPaymentOption?.link) return
          return decode(lnPaymentOption.link)
        } catch (error) {
          console.warn(error)
        }
      },

      merchantProfile: function (pubkey) {
        const merchant = this.merchants.find(m => m.publicKey === pubkey)
        return merchant?.profile
      },

      showInvoice: function (order) {
        if (order.paid) return
        const invoice = order?.payment_options?.find(p => p.type === 'ln').link
        if (!invoice) return
        this.$emit('show-invoice', invoice)
      },

      formatCurrency: function (value, unit) {
        return formatCurrency(value, unit)
      },

      fromNow: function (date) {
        if (!date) return ''
        return moment(date * 1000).fromNow()
      }
    },
    created() {
      console.log('### orders', this.orders)
      console.log('### products', this.products)
      console.log('### stall', this.stalls)
      console.log('### merchants', this.merchants)
    }
  })
}
