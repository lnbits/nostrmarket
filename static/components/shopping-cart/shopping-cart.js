async function shoppingCart(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart', {
    name: 'shopping-cart',
    template,

    props: [
      'cart',
      'cart-menu',
      'add-to-cart',
      'remove-from-cart',
      'reset-cart',
      'products'
    ],
    data: function () {
      return {}
    },
    computed: {},
    methods: {
      add(id) {
        this.$emit(
          'add-to-cart',
          this.products.find(p => p.id == id)
        )
      },
      remove(id) {
        this.$emit(
          'remove-from-cart',
          this.products.find(p => p.id == id)
        )
      }
    },
    created() {}
  })
}
