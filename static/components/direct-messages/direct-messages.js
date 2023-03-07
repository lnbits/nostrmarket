async function directMessages(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('direct-messages', {
    name: 'direct-messages',
    props: ['adminkey', 'inkey'],
    template,

    data: function () {
      return {}
    },
    methods: {},
    created: async function () {}
  })
}
