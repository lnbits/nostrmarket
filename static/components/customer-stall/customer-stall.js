async function customerStall(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: [
      'stall',
      'products',
      'exchange-rates',
      'product-detail',
      'change-page'
    ],
    data: function () {
      return {}
    },
    computed: {
      product() {
        if (this.productDetail) {
          return this.products.find(p => p.id == this.productDetail)
        }
      }
    },
    methods: {
      changePageS(page, opts) {
        this.$emit('change-page', page, opts)
      }
    },
    created() {}
  })
}
