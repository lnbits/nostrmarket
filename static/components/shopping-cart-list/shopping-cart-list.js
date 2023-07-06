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
      removeProduct: function (stallId, productId) {
        console.log('### stallId, productId', stallId, productId)
        this.$emit('remove-from-cart', { stallId, productId })
      }
    },
    created() { }
  })
}