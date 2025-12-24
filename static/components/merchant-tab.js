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
  emits: [
    'toggle-show-keys',
    'hide-keys',
    'merchant-deleted',
    'toggle-merchant-state',
    'restart-nostr-connection',
    'profile-updated'
  ],
  data: function () {
    return {
      showEditProfileDialog: false,
      showKeysDialog: false
    }
  },
  computed: {
    marketClientUrl: function () {
      return '/nostrmarket/market'
    }
  },
  methods: {
    publishProfile: async function () {
      try {
        await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/merchant/${this.merchantId}/nostr`,
          this.adminkey
        )
        this.$q.notify({
          type: 'positive',
          message: 'Profile published to Nostr!'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
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
    },
    handleImageError: function (e) {
      e.target.style.display = 'none'
    }
  }
})
