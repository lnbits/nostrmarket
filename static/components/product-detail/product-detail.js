async function productDetail(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('product-detail', {
    name: 'product-detail',
    template,

    props: ['product', 'add-to-cart'],
    data: function () {
      return {
        slide: 1
      }
    },
    computed: {},
    methods: {},
    created() {}
  })
}
