async function shoppingCartList(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart-list', {
    name: 'shopping-cart-list',
    template,

    props: ['carts', 'products'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {

    },
    created() { }
  })
}
