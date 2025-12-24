window.app.component('nostr-keys-dialog', {
  name: 'nostr-keys-dialog',
  template: '#nostr-keys-dialog',
  delimiters: ['${', '}'],
  props: ['public-key', 'private-key', 'model-value'],
  emits: ['update:model-value'],
  data: function () {
    return {
      showNsec: false
    }
  },
  computed: {
    show: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:model-value', value)
      }
    },
    npub: function () {
      if (!this.publicKey) return ''
      try {
        return window.NostrTools.nip19.npubEncode(this.publicKey)
      } catch (e) {
        return this.publicKey
      }
    },
    nsec: function () {
      if (!this.privateKey) return ''
      try {
        return window.NostrTools.nip19.nsecEncode(this.privateKey)
      } catch (e) {
        return this.privateKey
      }
    }
  },
  methods: {
    copyText: function (text, message) {
      var notify = this.$q.notify
      Quasar.copyToClipboard(text).then(function () {
        notify({
          message: message || 'Copied to clipboard!',
          position: 'bottom'
        })
      })
    }
  },
  watch: {
    modelValue(newVal) {
      if (!newVal) {
        this.showNsec = false
      }
    }
  }
})
