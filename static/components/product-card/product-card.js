async function productCard(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('product-card', {
    name: 'product-card',
    template,

    props: ['product'],
    data: function () {
      return {}
    },
    methods: {},
    created() {}
  })
}
