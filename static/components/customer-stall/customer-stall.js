async function customerStall(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: [
      'stall',
      'products',
      'product-detail',
    ],
    data: function () {
      return {
      }
    },
    computed: {
      product() {
        if (this.productDetail) {
          return this.products.find(p => p.id == this.productDetail)
        }
      },
    },
    methods: {
      changePageS(page, opts) {
        if (page === 'stall' && opts?.product) {
          document.getElementById('product-focus-area')?.scrollIntoView()
        }
        this.$emit('change-page', page, opts)
      },
      addToCart(item) {
        this.$emit('add-to-cart', item)
      },

    }
  })
}
