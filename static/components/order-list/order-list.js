async function orderList(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('order-list', {
      name: 'order-list',
      props: ['adminkey', 'inkey'],
      template,
  
      data: function () {
        return {
        }
      },
      methods: {
      },
      created: async function () {
      }
    })
  }
  