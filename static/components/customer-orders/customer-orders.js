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
        return Object.keys(this.orders)
          .map(pubkey => ({
            pubkey,
            profile: this.merchantProfile(pubkey),
            orders: this.orders[pubkey].map(this.enrichOrder)
          }
          ))
      }
    },
    methods: {
      enrichOrder: function (order) {
        const stall = this.stallForOrder(order)
        return {
          ...order,
          stallName: stall?.name || 'Stall',
          shippingZone: stall?.shipping?.find(s => s.id === order.shipping_id) || { id: order.shipping_id, name: order.shipping_id },
          invoice: this.invoiceForOrder(order),
          products: this.getProductsForOrder(order)
        }
      },
      stallForOrder: function (order) {
        try {
          const productId = order.items && order.items[0]?.product_id
          if (!productId) return
          const product = this.products.find(p => p.id === productId)
          if (!product) return
          const stall = this.stalls.find(s => s.id === product.stall_id)
          if (!stall) return
          return stall
        } catch (error) {
          console.log(error)
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

      getProductsForOrder: function (order) {
        if (!order?.items?.length) return []

        return order.items.map(i => {
          const product = this.products.find(p => p.id === i.product_id) || { id: i.product_id, name: i.product_id }
          return {
            ...product,
            orderedQuantity: i.quantity
          }
        })
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
