window.app.component('key-pair', {
  name: 'key-pair',
  template: '#key-pair',
  delimiters: ['${', '}'],
  props: ['public-key', 'private-key', 'merchant-config'],
  methods: {
    handleImageError: function (event) {
      event.target.style.display = 'none'
    }
  }
})
