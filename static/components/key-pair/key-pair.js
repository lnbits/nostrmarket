async function keyPair(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('key-pair', {
    name: 'key-pair',
    template,

    props: ['public-key', 'private-key'],
    data: function () {
      return {
        showPrivateKey: false
      }
    },
    methods: {
      copyText: function (text, message, position) {
        var notify = this.$q.notify
        Quasar.utils.copyToClipboard(text).then(function () {
          notify({
            message: message || 'Copied to clipboard!',
            position: position || 'bottom'
          })
        })
      }
    }
  })
}
