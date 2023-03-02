async function customerStall(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: ['stall', 'products', 'exchange-rates'],
    data: function () {
      return {}
    },
    methods: {},
    created() {
      console.log(this.stall)
      console.log(this.products)
    }
  })
}
