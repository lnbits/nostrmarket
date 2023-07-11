async function customerOrders(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-orders', {
    name: 'orders',
    template,

    props: ['orders'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {
    
    },
    created() { 
      console.log('### orders', this.orders)
    }
  })
}
