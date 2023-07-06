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
      'update-stalls',
      'styles'
    ],
    data: function () {
      return {
        search: null,
        partialProducts: [],
        productsPerPage: 24,
        startIndex: 0,
        lastProductIndex: 0
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
        pool.close(relays)
        await this.$emit('update-data', [...stallEvents, ...productEvents])
        this.$q.loading.hide()
      },
      onLoad(_, done) {
        setTimeout(() => {
          if (this.startIndex >= this.products.length) {
            done()
            return
          }
          this.startIndex = this.lastProductIndex
          this.lastProductIndex = Math.min(this.products.length, this.lastProductIndex + this.productsPerPage)
          this.partialProducts.push(...this.products.slice(this.startIndex, this.lastProductIndex))
          done()
        }, 100)
      }
    },
    created() {
      this.lastProductIndex = Math.min(this.products.length, 24)
      this.partialProducts.push(...this.products.slice(0, this.lastProductIndex))
    }
  })
}
