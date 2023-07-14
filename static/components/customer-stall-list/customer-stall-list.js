async function customerStallList(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall-list', {
    name: 'customer-stall-list',
    template,

    props: ['stalls'],
    data: function () {
      return {}
    },
    computed: {},
    methods: {

    },
    created() {
      console.log('### stalls', this.stalls)
    }
  })
}
