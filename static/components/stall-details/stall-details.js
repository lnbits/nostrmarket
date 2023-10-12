async function stallDetails(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('stall-details', {
    name: 'stall-details',
    template,

    props: [
      'stall-id',
      'adminkey',
      'inkey',
      'wallet-options',
      'zone-options',
      'currencies'
    ],
    data: function () {
      return {
        tab: 'products',
        stall: null,
        products: [],
        pendingProducts: [],
        productDialog: {
          showDialog: false,
          showRestore: false,
          url: true,
          data: null
        },
        productsFilter: '',
        productsTable: {
          columns: [
            {
              name: 'delete',
              align: 'left',
              label: '',
              field: ''
            },
            {
              name: 'edit',
              align: 'left',
              label: '',
              field: ''
            },
            {
              name: 'activate',
              align: 'left',
              label: '',
              field: ''
            },

            {
              name: 'id',
              align: 'left',
              label: 'ID',
              field: 'id'
            },
            {
              name: 'name',
              align: 'left',
              label: 'Name',
              field: 'name'
            },
            {
              name: 'price',
              align: 'left',
              label: 'Price',
              field: 'price'
            },
            {
              name: 'quantity',
              align: 'left',
              label: 'Quantity',
              field: 'quantity'
            }
          ],
          pagination: {
            rowsPerPage: 10
          }
        }
      }
    },
    computed: {
      filteredZoneOptions: function () {
        if (!this.stall) return []
        return this.zoneOptions.filter(z => z.currency === this.stall.currency)
      }
    },
    methods: {
      mapStall: function (stall) {
        stall.shipping_zones.forEach(
          z =>
          (z.label = z.name
            ? `${z.name} (${z.countries.join(', ')})`
            : z.countries.join(', '))
        )
        return stall
      },
      newEmtpyProductData: function() {
        return {
          id: null,
          name: '',
          categories: [],
          images: [],
          image: null,
          price: 0,

          quantity: 0,
          config: {
            description: '',
            use_autoreply: false,
            autoreply_message: '',
            shipping: (this.stall.shipping_zones || []).map(z => ({id: z.id, name: z.name, cost: 0}))
          }
        }
      },
      getStall: async function () {
        try {
          const { data } = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.inkey
          )
          this.stall = this.mapStall(data)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      updateStall: async function () {
        try {
          const { data } = await LNbits.api.request(
            'PUT',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.adminkey,
            this.stall
          )
          this.stall = this.mapStall(data)
          this.$emit('stall-updated', this.stall)
          this.$q.notify({
            type: 'positive',
            message: 'Stall Updated',
            timeout: 5000
          })
        } catch (error) {
          console.warn(error)
          LNbits.utils.notifyApiError(error)
        }
      },
      deleteStall: function () {
        LNbits.utils
          .confirmDialog(
            `
             Products and orders will be deleted also!
             Are you sure you want to delete this stall?
            `
          )
          .onOk(async () => {
            try {
              await LNbits.api.request(
                'DELETE',
                '/nostrmarket/api/v1/stall/' + this.stallId,
                this.adminkey
              )
              this.$emit('stall-deleted', this.stallId)
              this.$q.notify({
                type: 'positive',
                message: 'Stall Deleted',
                timeout: 5000
              })
            } catch (error) {
              console.warn(error)
              LNbits.utils.notifyApiError(error)
            }
          })
      },
      addProductImage: function () {
        if (!isValidImageUrl(this.productDialog.data.image)) {
          this.$q.notify({
            type: 'warning',
            message: 'Not a valid image URL',
            timeout: 5000
          })
          return
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
      getProducts: async function (pending = false) {
        try {
          const { data } = await LNbits.api.request(
            'GET',
            `/nostrmarket/api/v1/stall/product/${this.stall.id}?pending=${pending}`,
            this.inkey
          )
          return data
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      sendProductFormData: function () {
        const data = {
          stall_id: this.stall.id,
          id: this.productDialog.data.id,
          name: this.productDialog.data.name,

          images: this.productDialog.data.images,
          price: this.productDialog.data.price,
          quantity: this.productDialog.data.quantity,
          categories: this.productDialog.data.categories,
          config: this.productDialog.data.config
        }
        this.productDialog.showDialog = false
        if (this.productDialog.data.id) {
          data.pending = false
          this.updateProduct(data)
        } else {
          this.createProduct(data)
        }
      },
      updateProduct: async function (product) {
        try {
          const { data } = await LNbits.api.request(
            'PATCH',
            '/nostrmarket/api/v1/product/' + product.id,
            this.adminkey,
            product
          )
          const index = this.products.findIndex(r => r.id === product.id)
          if (index !== -1) {
            this.products.splice(index, 1, data)
          } else {
            this.products.unshift(data)
          }
          this.$q.notify({
            type: 'positive',
            message: 'Product Updated',
            timeout: 5000
          })
        } catch (error) {
          console.warn(error)
          LNbits.utils.notifyApiError(error)
        }
      },
      createProduct: async function (payload) {
        try {
          const { data } = await LNbits.api.request(
            'POST',
            '/nostrmarket/api/v1/product',
            this.adminkey,
            payload
          )
          this.products.unshift(data)
          this.$q.notify({
            type: 'positive',
            message: 'Product Created',
            timeout: 5000
          })
        } catch (error) {
          console.warn(error)
          LNbits.utils.notifyApiError(error)
        }
      },
      editProduct: async function (product) {
        const emptyShipping = this.newEmtpyProductData().config.shipping
        this.productDialog.data = { ...product }
        this.productDialog.data.config.shipping = emptyShipping.map(shippingZone => {
          const existingShippingCost = (product.config.shipping || []).find(ps => ps.id === shippingZone.id)
          shippingZone.cost = existingShippingCost?.cost || 0
          return shippingZone
        })
        
        this.productDialog.showDialog = true
      },
      deleteProduct: async function (productId) {
        LNbits.utils
          .confirmDialog('Are you sure you want to delete this product?')
          .onOk(async () => {
            try {
              await LNbits.api.request(
                'DELETE',
                '/nostrmarket/api/v1/product/' + productId,
                this.adminkey
              )
              this.products = _.reject(this.products, function (obj) {
                return obj.id === productId
              })
              this.$q.notify({
                type: 'positive',
                message: 'Product deleted',
                timeout: 5000
              })
            } catch (error) {
              console.warn(error)
              LNbits.utils.notifyApiError(error)
            }
          })
      },
      showNewProductDialog: async function (data) {
        this.productDialog.data = data || this.newEmtpyProductData()
        this.productDialog.showDialog = true
      },
      openSelectPendingProductDialog: async function () {
        this.productDialog.showRestore = true
        this.pendingProducts = await this.getProducts(true)
      },
      openRestoreProductDialog: async function (pendingProduct) {
        pendingProduct.pending = true
        await this.showNewProductDialog(pendingProduct)
      },
      restoreAllPendingProducts: async function () {
        for (const p of this.pendingProducts){
          p.pending = false
          await this.updateProduct(p)
        }
      },
      customerSelectedForOrder: function (customerPubkey) {
        this.$emit('customer-selected-for-order', customerPubkey)
      },
      shortLabel(value = ''){
        if (value.length <= 44) return value
        return value.substring(0, 40) + '...'
      }
    },
    created: async function () {
      await this.getStall()
      this.products = await this.getProducts()
      this.productDialog.data = this.newEmtpyProductData()
    }
  })
}
