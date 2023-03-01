async function customerMarket(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('customer-market', {
    name: 'customer-market',
    template,

    props: ['products', 'exchange-rates'],
    data: function () {
      return {}
    },
    methods: {
      changePage() {
        return
      }
    }
  })
}
