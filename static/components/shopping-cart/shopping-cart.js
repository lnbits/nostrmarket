async function shoppingCart(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart', {
    name: 'shopping-cart',
    template,

    props: [],
    data: function () {
      return {}
    },
    computed: {},
    methods: {},
    created() {}
  })
}
