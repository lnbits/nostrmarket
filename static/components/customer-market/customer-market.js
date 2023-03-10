async function customerMarket(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('customer-market', {
    name: 'customer-market',
    template,

    props: [
      'products',
      'change-page',
      'search-nostr',
      'relays',
      'update-products',
      'update-stalls'
    ],
    data: function () {
      return {
        search: null
      }
    },
    methods: {
      changePageM(page, opts) {
        this.$emit('change-page', page, opts)
      },
      async searchProducts() {
        this.$q.loading.show()
        let searchTags = this.search.split(' ')
        const pool = new NostrTools.SimplePool()
        let relays = Array.from(this.relays)

        let merchants = new Set()
        let productEvents = await pool.list(relays, [
          {
            kinds: [30018],
            '#t': searchTags,
            search: this.search, // NIP50, not very well supported
            limit: 100
          }
        ])
        productEvents.map(e => merchants.add(e.pubkey))
        let stallEvents = await pool.list(relays, [
          {
            kinds: [30017],
            authors: Array.from(merchants)
          }
        ])
        await this.$emit('update-data', [...stallEvents, ...productEvents])
        this.$q.loading.hide()
      }
    },
    created() {}
  })
}
