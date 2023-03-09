async function shoppingCart(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart', {
    name: 'shopping-cart',
    template,

    props: ['cart', 'cart-menu', 'remove-from-cart', 'reset-cart'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {},
    created() {}
  })
}
