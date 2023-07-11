async function customerOrders(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-orders', {
    name: 'orders',
    template,

    props: ['orders', 'products', 'stalls'],
    data: function () {
      return {}
    },
    computed: {
      merchantOrders: function () {
        return Object.keys(this.orders).map(pubkey => ({ pubkey, orders: this.orders[pubkey] }))
      }
    },
    methods: {
      stallNameForOrder: function (order) {
        console.log('### stallNameForOrder', order)
        const productId = order.items[0]?.product_id
        if (!productId) return 'Stall Name'
        const product = this.products.find(p => p.id === productId)
        if (!product) return 'Stall Name'
        const stall = this.stalls.find(s => s.id === product.stall_id)
        if (!stall) return 'Stall Name'
        return stall.name
      }

    },
    created() {
      console.log('### orders', this.orders)
      console.log('### products', this.products)
      console.log('### stall', this.stalls)
    }
  })
}
