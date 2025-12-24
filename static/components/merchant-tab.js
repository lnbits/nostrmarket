window.app.component('merchant-tab', {
  name: 'merchant-tab',
  template: '#merchant-tab',
  delimiters: ['${', '}'],
  props: [
    'merchant-id',
    'inkey',
    'adminkey',
    'show-keys',
    'merchant-active',
    'public-key',
    'private-key',
    'is-admin',
    'merchant-config'
  ],
  computed: {
    marketClientUrl: function () {
      return '/nostrmarket/market'
    }
  },
  methods: {
    toggleShowKeys: function () {
      this.$emit('toggle-show-keys')
    },
    hideKeys: function () {
      this.$emit('hide-keys')
    },
    handleMerchantDeleted: function () {
      this.$emit('merchant-deleted')
    },
    toggleMerchantState: function () {
      this.$emit('toggle-merchant-state')
    },
    restartNostrConnection: function () {
      this.$emit('restart-nostr-connection')
    }
  }
})
