async function shoppingCartCheckout(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart-checkout', {
    name: 'shopping-cart-checkout',
    template,

    props: ['cart', 'stall'],
    data: function () {
      return {
        paymentMethod: 'ln',
        shippingZone: null,
        contactData: {
          email: null,
          address: null,
          message: null
        },
        paymentOptions: [
          {
            label: 'Lightning Network',
            value: 'ln'
          },
          {
            label: 'BTC Onchain',
            value: 'btc'
          },
          {
            label: 'Cashu',
            value: 'cashu'
          }
        ]
      }
    },
    computed: {
      cartTotal() {
        if (!this.cart.products?.length) return 0
        return this.cart.products.reduce((t, p) => p.price + t, 0)
      },
      cartTotalWithShipping() {
        if (!this.shippingZone) return this.cartTotal
        return this.cartTotal + this.shippingZone.cost
      },
      shippingZoneLabel() {
        if (!this.shippingZone) {
          return 'Shipping Zone'
        }
        const zoneName = this.shippingZone.name.substring(0, 10)
        if (this.shippingZone?.name.length < 10) {
          return zoneName
        }
        return zoneName + '...'
      }
    },
    methods: {
      formatCurrency: function (value, unit) {
        return formatCurrency(value, unit)
      },
      selectShippingZone: function (zone) {
        this.shippingZone = zone
      },
      requestInvoice: function () {

      }
    },
    created() {
      console.log('### shoppingCartCheckout', this.stall)
      if (this.stall.shipping?.length === 1) {
        this.shippingZone = this.stall.shipping[0]
      }
    }
  })
}
