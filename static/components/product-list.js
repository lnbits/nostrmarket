window.app.component('product-list', {
  name: 'product-list',
  template: '#product-list',
  delimiters: ['${', '}'],
  props: ['adminkey', 'inkey', 'stall-filter'],
  data: function () {
    return {
      filter: '',
      stalls: [],
      products: [],
      pendingProducts: [],
      selectedStall: null,
      productDialog: {
        showDialog: false,
        showRestore: false,
        data: null
      },
      productsTable: {
        columns: [
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {name: 'stall', align: 'left', label: 'Stall', field: 'stall_id'},
          {name: 'price', align: 'left', label: 'Price', field: 'price'},
          {name: 'quantity', align: 'left', label: 'Quantity', field: 'quantity'},
          {name: 'actions', align: 'right', label: 'Actions', field: ''}
        ],
        pagination: {
          rowsPerPage: 10
        }
      }
    }
  },
  computed: {
    stallOptions: function () {
      return this.stalls.map(s => ({
        label: s.name,
        value: s.id
      }))
    },
    filteredProducts: function () {
      if (!this.selectedStall) {
        return this.products
      }
      return this.products.filter(p => p.stall_id === this.selectedStall)
    }
  },
  watch: {
    stallFilter: {
      immediate: true,
      handler(newVal) {
        if (newVal) {
          this.selectedStall = newVal
        }
      }
    }
  },
  methods: {
    getStalls: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/stall?pending=false',
          this.inkey
        )
        this.stalls = data
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getProducts: async function () {
      try {
        // Fetch products from all stalls
        const allProducts = []
        for (const stall of this.stalls) {
          const {data} = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/stall/product/${stall.id}?pending=false`,
            this.inkey
          )
          allProducts.push(...data)
        }
        this.products = allProducts
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getPendingProducts: async function () {
      try {
        // Fetch pending products from all stalls
        const allPending = []
        for (const stall of this.stalls) {
          const {data} = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/stall/product/${stall.id}?pending=true`,
            this.inkey
          )
          allPending.push(...data)
        }
        this.pendingProducts = allPending
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getStallName: function (stallId) {
      const stall = this.stalls.find(s => s.id === stallId)
      return stall ? stall.name : 'Unknown'
    },
    getStallCurrency: function (stallId) {
      const stall = this.stalls.find(s => s.id === stallId)
      return stall ? stall.currency : 'sat'
    },
    getStall: function (stallId) {
      return this.stalls.find(s => s.id === stallId)
    },
    newEmptyProductData: function () {
      return {
        id: null,
        stall_id: this.stalls.length ? this.stalls[0].id : null,
        name: '',
        categories: [],
        images: [],
        image: null,
        price: 0,
        quantity: 0,
        config: {
          description: '',
          use_autoreply: false,
          autoreply_message: ''
        }
      }
    },
    showNewProductDialog: function () {
      this.productDialog.data = this.newEmptyProductData()
      this.productDialog.showDialog = true
    },
    editProduct: function (product) {
      this.productDialog.data = {...product, image: null}
      if (!this.productDialog.data.config) {
        this.productDialog.data.config = {description: ''}
      }
      this.productDialog.showDialog = true
    },
    sendProductFormData: async function () {
      const data = {
        stall_id: this.productDialog.data.stall_id,
        id: this.productDialog.data.id,
        name: this.productDialog.data.name,
        images: this.productDialog.data.images || [],
        price: this.productDialog.data.price,
        quantity: this.productDialog.data.quantity,
        categories: this.productDialog.data.categories || [],
        config: this.productDialog.data.config
      }
      this.productDialog.showDialog = false

      if (this.productDialog.data.id) {
        data.pending = false
        await this.updateProduct(data)
      } else {
        await this.createProduct(data)
      }
    },
    createProduct: async function (payload) {
      try {
        const {data} = await LNbits.api.request(
          'POST',
          '/nostrmarket/api/v1/product',
          this.adminkey,
          payload
        )
        this.products.unshift(data)
        this.$q.notify({
          type: 'positive',
          message: 'Product Created'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    updateProduct: async function (product) {
      try {
        const {data} = await LNbits.api.request(
          'PATCH',
          '/nostrmarket/api/v1/product/' + product.id,
          this.adminkey,
          product
        )
        const index = this.products.findIndex(p => p.id === product.id)
        if (index !== -1) {
          this.products.splice(index, 1, data)
        } else {
          this.products.unshift(data)
        }
        this.$q.notify({
          type: 'positive',
          message: 'Product Updated'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    deleteProduct: function (product) {
      LNbits.utils
        .confirmDialog(`Are you sure you want to delete "${product.name}"?`)
        .onOk(async () => {
          try {
            await LNbits.api.request(
              'DELETE',
              '/nostrmarket/api/v1/product/' + product.id,
              this.adminkey
            )
            this.products = this.products.filter(p => p.id !== product.id)
            this.$q.notify({
              type: 'positive',
              message: 'Product Deleted'
            })
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    toggleProductActive: async function (product) {
      await this.updateProduct({...product, active: !product.active})
    },
    addProductImage: function () {
      if (!this.productDialog.data.image) return
      if (!this.productDialog.data.images) {
        this.productDialog.data.images = []
      }
      this.productDialog.data.images.push(this.productDialog.data.image)
      this.productDialog.data.image = null
    },
    removeProductImage: function (imageUrl) {
      const index = this.productDialog.data.images.indexOf(imageUrl)
      if (index !== -1) {
        this.productDialog.data.images.splice(index, 1)
      }
    },
    openSelectPendingProductDialog: async function () {
      await this.getPendingProducts()
      this.productDialog.showRestore = true
    },
    openRestoreProductDialog: function (pendingProduct) {
      pendingProduct.pending = true
      this.productDialog.data = {...pendingProduct, image: null}
      this.productDialog.showDialog = true
    },
    shortLabel: function (value = '') {
      if (value.length <= 44) return value
      return value.substring(0, 40) + '...'
    }
  },
  created: async function () {
    await this.getStalls()
    await this.getProducts()
  }
})
