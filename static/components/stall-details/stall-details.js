async function stallDetails(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('stall-details', {
    name: 'stall-details',
    template,

    //props: ['stall-id', 'adminkey', 'inkey', 'wallet-options'],
    data: function () {
      return {
        tab: 'info',
        relay: null
      }
    }
  })
}
