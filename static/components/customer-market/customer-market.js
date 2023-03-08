async function customerMarket(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('customer-market', {
    name: 'customer-market',
    template,

    props: ['products', 'change-page'],
    data: function () {
      return {}
    },
    methods: {
      changePageM(page, opts) {
        this.$emit('change-page', page, opts)
      }
    },
    created() {}
  })
}
