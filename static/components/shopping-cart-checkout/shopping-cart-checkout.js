async function shoppingCartCheckout(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart-checkout', {
    name: 'shopping-cart-checkout',
    template,

    props: ['cart'],
    data: function () {
      return {
        paymentMethod: 'ln',
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
    },
    methods: {
      formatCurrency: function (value, unit) {
        return formatCurrency(value, unit)
      },
      requestInvoice: function () {

      }
    },
    created() {
      console.log('### shoppingCartCheckout', this.cart)
    }
  })
}
