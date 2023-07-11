async function customerOrders(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-orders', {
    name: 'customer-orders',
    template,

    props: ['orders'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {
    
    },
    created() { }
  })
}
