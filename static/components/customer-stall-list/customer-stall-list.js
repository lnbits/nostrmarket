async function customerStallList(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall-list', {
    name: 'customer-stall-list',
    template,

    props: ['stalls'],
    data: function () {
      return {
        showStalls: true
      }
    },
    watch: {
      stalls() {
        this.showProducts = false
        setTimeout(() => { this.showProducts = true }, 0)
      }
    },
    computed: {},
    methods: {

    },
    created() {
    }
  })
}
