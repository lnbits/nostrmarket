async function shoppingCart(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart', {
    name: 'shopping-cart',
    template,

    props: [
      'cart',
      'cart-menu',
      'add-to-cart',
      'remove-from-cart',
      'update-qty',
      'reset-cart',
      'products'
    ],
    data: function () {
      return {}
    },
    computed: {},
    methods: {
      add(id) {
        this.$emit(
          'add-to-cart',
          this.products.find(p => p.id == id)
        )
      },
      remove(id) {
        this.$emit(
          'remove-from-cart',
          this.products.find(p => p.id == id)
        )
      },
      removeProduct(id) {
        this.$emit(
          'remove-from-cart',
          this.products.find(p => p.id == id),
          true
        )
      },
      addQty(id, qty) {
        if (qty == 0) {
          return this.removeProduct(id)
        }
        let product = this.products.find(p => p.id == id)
        if (product.quantity < qty) {
          this.$q.notify({
            type: 'warning',
            message: `${product.name} only has ${product.quantity} units!`,
            icon: 'production_quantity_limits'
          })
          let objIdx = this.cartMenu.findIndex(pr => pr.id == id)
          this.cartMenu[objIdx].quantity = this.cart.products.get(id).quantity
          return
        }
        this.$emit('update-qty', id, qty)
      }
    },
    created() {}
  })
}
