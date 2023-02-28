async function shippingZones(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('shipping-zones', {
    name: 'shipping-zones',
    template,

    data: function () {
      return {
        zones: []
      }
    },
    methods: {
      createShippingZone: async function () {
        console.log('### createShippingZone', createShippingZone)
      },
      editShippingZone: async function () {}
    }
  })
}
