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
      'styles',

      'search-text'
    ],
    data: function () {
      return {
        search: null,
        partialProducts: [],
        filteredProducts: [],
        productsPerPage: 24,
        startIndex: 0,
        lastProductIndex: 0,
        showProducts: true,
      }
    },
    watch: {
      searchText: function () {
        this.refreshProducts()
      },
      products: function () {
        this.refreshProducts()
      }
    },
    methods: {
      refreshProducts: function() {
        this.showProducts = false
        const searchText = this.searchText?.toLowerCase() || ''
        this.partialProducts = []
        if (searchText.length < 3) {
          this.filteredProducts = [...this.products]
          this.lastProductIndex = Math.min(this.filteredProducts.length, 24)
          this.partialProducts.push(...this.filteredProducts.slice(0, this.lastProductIndex))
          setTimeout(() => this.showProducts = true, 0)
          return
        }

        
        this.filteredProducts = this.products.filter(p => {
          return (
            p.name.toLowerCase().includes(searchText) ||
            (p.description &&
              p.description.toLowerCase().includes(searchText)) ||
            (p.categories &&
              p.categories.toString().toLowerCase().includes(searchText))
          )
        })
        this.startIndex = 0
        this.lastProductIndex = Math.min(this.filteredProducts.length, 24)
        this.partialProducts.push(...this.filteredProducts.slice(0, this.lastProductIndex))

        setTimeout(() => { this.showProducts = true }, 0)
        console.log('### xxx this.filteredProducts', this.lastProductIndex, this.filteredProducts)
      },
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
          if (this.startIndex >= this.filteredProducts.length) {
            done()
            return
          }
          this.startIndex = this.lastProductIndex
          this.lastProductIndex = Math.min(this.filteredProducts.length, this.lastProductIndex + this.productsPerPage)
          this.partialProducts.push(...this.filteredProducts.slice(this.startIndex, this.lastProductIndex))
          done()
        }, 100)
      }
    },
    created() {
      this.filteredProducts = [...this.products]
      console.log('#### created  this.filteredProducts',  this.filteredProducts)
      this.lastProductIndex = Math.min(this.filteredProducts.length, 24)
      this.partialProducts.push(...this.filteredProducts.slice(0, this.lastProductIndex))
    }
  })
}
