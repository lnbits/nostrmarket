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
    'profile-updated',
    'import-key',
    'generate-key'
  ],
  data: function () {
    return {
      showEditProfileDialog: false,
      showKeysDialog: false
    }
  },
  computed: {
    marketClientUrl: function () {
      if (!this.publicKey) {
        return '/nostrmarket/market'
      }

      const url = new URL('/nostrmarket/market', window.location.origin)
      url.searchParams.set('merchant', this.publicKey)
      return url.pathname + url.search
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
    removeMerchant: function () {
      const name =
        this.merchantConfig?.display_name ||
        this.merchantConfig?.name ||
        'this merchant'
      LNbits.utils
        .confirmDialog(
          `Are you sure you want to remove "${name}"? This will delete all associated data (stalls, products, orders, messages).`
        )
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              `/nostrmarket/api/v1/merchant/${this.merchantId}`,
              this.adminkey
            )
            this.$emit('merchant-deleted')
            this.$q.notify({
              type: 'positive',
              message: 'Merchant removed'
            })
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
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
