async function shoppingCartList(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart-list', {
    name: 'shopping-cart-list',
    template,

    props: ['carts'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {
      formatCurrency: function (value, unit) {
        return formatCurrency(value, unit)
      },
      cartTotalFormatted(cart) {
        if (!cart.products?.length) return ""
        const total = cart.products.reduce((t, p) => p.price + t, 0)
        return formatCurrency(total, cart.products[0].currency)
      },
      removeProduct: function (stallId, productId) {
        this.$emit('remove-from-cart', { stallId, productId })
      },
      quantityChanged: function (product) {
        this.$emit('add-to-cart', product)
      }
    },
    created() { }
  })
}
