async function productDetail(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('product-detail', {
    name: 'product-detail',
    template,

    props: ['product'],
    data: function () {
      return {
        slide: 1
      }
    },
    computed: {
      win_width() {
        return this.$q.screen.width - 59
      },
      win_height() {
        return this.$q.screen.height - 0
      }
    },
    methods: {},
    created() {
      console.log('ping')
    }
  })
}
