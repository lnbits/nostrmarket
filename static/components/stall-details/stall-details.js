async function stallDetails(path) {
  const template = await loadTemplateAsync(path)

  const pica = window.pica()

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
        productDialog: {
          showDialog: false,
          url: true,
          data: {
            id: null,
            name: '',
            categories: [],
            image: null,
            price: 0,

            quantity: 0,
            config: {
              description: ''
            }
          }
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
            },
            {
              name: 'categories',
              align: 'left',
              label: 'Categories',
              field: 'categories'
            },
            {
              name: 'description',
              align: 'left',
              label: 'Description',
              field: 'description'
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
      getStall: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/stall/' + this.stallId,
            this.inkey
          )
          this.stall = this.mapStall(data)

          console.log('### this.stall', this.stall)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      updateStall: async function () {
        try {
          const {data} = await LNbits.api.request(
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
      imageAdded(file) {
        const image = new Image()
        image.src = URL.createObjectURL(file)
        image.onload = async () => {
          let fit = imgSizeFit(image)
          let canvas = document.createElement('canvas')
          canvas.setAttribute('width', fit.width)
          canvas.setAttribute('height', fit.height)
          output = await pica.resize(image, canvas)
          this.productDialog.data.image = output.toDataURL('image/jpeg', 0.4)
          this.productDialog = {...this.productDialog}
        }
      },
      imageCleared() {
        this.productDialog.data.image = null
        this.productDialog = {...this.productDialog}
      },
      getProducts: async function () {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/stall/product/' + this.stall.id,
            this.inkey
          )
          this.products = data

          console.log('### this.products', this.products)
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      },
      sendProductFormData: function () {
        var data = {
          stall_id: this.stall.id,
          id: this.productDialog.data.id,
          name: this.productDialog.data.name,

          image: this.productDialog.data.image,
          price: this.productDialog.data.price,
          quantity: this.productDialog.data.quantity,
          categories: this.productDialog.data.categories,
          config: this.productDialog.data.config
        }
        this.productDialog.showDialog = false
        if (this.productDialog.data.id) {
          this.updateProduct(data)
        } else {
          this.createProduct(data)
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
          const index = this.products.findIndex(r => r.id === product.id)
          if (index !== -1) {
            this.products.splice(index, 1, data)
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
          const {data} = await LNbits.api.request(
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
        this.productDialog.data = {...product}
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
      showNewProductDialog: async function () {
        this.productDialog.data = {
          id: null,
          name: '',
          description: '',
          categories: [],
          image: null,
          price: 0,
          quantity: 0,
          config: {
            description: ''
          }
        }
        this.productDialog.showDialog = true
      }
    },
    created: async function () {
      await this.getStall()
      await this.getProducts()
    }
  })
}
