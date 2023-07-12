async function shoppingCartCheckout(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('shopping-cart-checkout', {
    name: 'shopping-cart-checkout',
    template,

    props: ['cart', 'stall', 'customer-pubkey'],
    data: function () {
      return {
        orderConfirmed: false,
        paymentMethod: 'ln',
        shippingZone: null,
        contactData: {
          email: null,
          npub: null,
          address: null,
          message: null
        },
        paymentOptions: [
          {
            label: 'Lightning Network',
            value: 'ln'
          },
          {
            label: 'BTC Onchain',
            value: 'btc'
          },
          {
            label: 'Cashu',
            value: 'cashu'
          }
        ]
      }
    },
    computed: {
      cartTotal() {
        if (!this.cart.products?.length) return 0
        return this.cart.products.reduce((t, p) => p.price + t, 0)
      },
      cartTotalWithShipping() {
        if (!this.shippingZone) return this.cartTotal
        return this.cartTotal + this.shippingZone.cost
      },
      shippingZoneLabel() {
        if (!this.shippingZone) {
          return 'Shipping Zone'
        }
        const zoneName = this.shippingZone.name.substring(0, 10)
        if (this.shippingZone?.name.length < 10) {
          return zoneName
        }
        return zoneName + '...'
      }
    },
    methods: {
      formatCurrency: function (value, unit) {
        return formatCurrency(value, unit)
      },
      selectShippingZone: function (zone) {
        this.shippingZone = zone
      },

      confirmOrder: function () {
        if (!this.shippingZone) {
          this.$q.notify({
            timeout: 5000,
            type: 'warning',
            message: 'Please select a shipping zone!',
          })
          return
        }
        this.orderConfirmed = true
      },
      async placeOrder() {
        if (!this.shippingZone) {
          this.$q.notify({
            timeout: 5000,
            type: 'warning',
            message: 'Please select a shipping zone!',
          })
          return
        }
        if (!this.customerPubkey) {
          this.$emit('login-required')
          return
        }
        const order = {
          address: this.contactData.address,
          message: this.contactData.message,
          contact: {
            nostr: this.contactData.npub,
            email: this.contactData.email
          },
          items: Array.from(this.cart.products, p => {
            return { product_id: p.id, quantity: p.orderedQuantity }
          }),
          shipping_id: this.shippingZone.id,
          type: 0
        }
        const created_at = Math.floor(Date.now() / 1000)
        order.id = await hash(
          [this.customerPubkey, created_at, JSON.stringify(order)].join(':')
        )

        const event = {
          ...(await NostrTools.getBlankEvent()),
          kind: 4,
          created_at,
          tags: [['p', this.stall.pubkey]],
          pubkey: this.customerPubkey
        }

        this.$emit('place-order', { event, order, cartId: this.cart.id })

      },
      goToShoppingCart: function () {
        this.$emit('change-page', 'shopping-cart-list')
      }
    },
    created() {
      if (this.stall.shipping?.length === 1) {
        this.shippingZone = this.stall.shipping[0]
      }
    }
  })
}
