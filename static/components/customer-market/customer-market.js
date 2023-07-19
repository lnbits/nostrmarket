async function customerMarket(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('customer-market', {
    name: 'customer-market',
    template,

    props: ['filtered-products', 'search-text', 'filter-categories'],
    data: function () {
      return {
        search: null,
        partialProducts: [],
        productsPerPage: 12,
        startIndex: 0,
        lastProductIndex: 0,
        showProducts: true,
      }
    },
    watch: {
      searchText: function () {
        this.refreshProducts()
      },
      filteredProducts: function () {
        this.refreshProducts()
      },
      filterCategories: function () {
        this.refreshProducts()
      }
    },
    methods: {
      refreshProducts: function () {
        this.showProducts = false
        this.partialProducts = []

        this.startIndex = 0
        this.lastProductIndex = Math.min(this.filteredProducts.length, this.productsPerPage)
        this.partialProducts.push(...this.filteredProducts.slice(0, this.lastProductIndex))

        setTimeout(() => { this.showProducts = true }, 0)
      },

      addToCart(item) {
        this.$emit('add-to-cart', item)
      },
      changePageM(page, opts) {
        this.$emit('change-page', page, opts)
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
      this.lastProductIndex = Math.min(this.filteredProducts.length, 24)
      this.partialProducts.push(...this.filteredProducts.slice(0, this.lastProductIndex))
    }
  })
}
