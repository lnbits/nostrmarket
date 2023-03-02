async function productDetail(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('product-detail', {
    name: 'product-detail',
    template,

    props: ['product'],
    data: function () {
      return {}
    },
    methods: {}
  })
}
