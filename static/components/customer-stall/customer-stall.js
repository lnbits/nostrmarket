async function customerStall(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: [
      'stall',
      'products',
      'exchange-rates',
      'product-detail',
      'change-page',
      'relays'
    ],
    data: function () {
      return {
        cart: {
          total: 0,
          size: 0,
          products: new Map()
        },
        cartMenu: [],
        hasNip07: false,
        checkoutDialog: {
          show: false,
          data: {
            pubkey: null
          }
        },
        qrCodeDialog: {
          data: {
            payment_request: null
          },
          show: false
        }
      }
    },
    computed: {
      product() {
        if (this.productDetail) {
          return this.products.find(p => p.id == this.productDetail)
        }
      },
      finalCost() {
        if (!this.checkoutDialog.data.shippingzone) return this.cart.total

        let zoneCost = this.stall.shipping.find(
          z => z.id == this.checkoutDialog.data.shippingzone
        )
        return +this.cart.total + zoneCost.cost
      }
    },
    methods: {
      changePageS(page, opts) {
        this.$emit('change-page', page, opts)
      },
      getValueInSats(amount, unit = 'USD') {
        if (!this.exchangeRates) return 0
        return Math.ceil(
          (amount / this.exchangeRates[`BTC${unit}`][unit]) * 1e8
        )
      },
      getAmountFormated(amount, unit = 'USD') {
        return LNbits.utils.formatCurrency(amount, unit)
      },
      addToCart(item) {
        console.log('add to cart', item)
        let prod = this.cart.products
        if (prod.has(item.id)) {
          let qty = prod.get(item.id).quantity
          prod.set(item.id, {
            ...prod.get(item.id),
            quantity: qty + 1
          })
        } else {
          prod.set(item.id, {
            name: item.name,
            quantity: 1,
            price: item.price,
            image: item?.images[0] || null
          })
        }
        this.$q.notify({
          type: 'positive',
          message: `${item.name} added to cart`,
          icon: 'thumb_up'
        })
        this.cart.products = prod
        this.updateCart(+item.price)
      },
      removeFromCart(item) {
        this.cart.products.delete(item.id)
        this.updateCart(+item.price, true)
      },
      updateCart(price, del = false) {
        console.log(this.cart, this.cartMenu)
        if (del) {
          this.cart.total -= price
          this.cart.size--
        } else {
          this.cart.total += price
          this.cart.size++
        }
        this.cartMenu = Array.from(this.cart.products, item => {
          return {id: item[0], ...item[1]}
        })
        console.log(this.cart, this.cartMenu)
      },
      resetCart() {
        this.cart = {
          total: 0,
          size: 0,
          products: new Map()
        }
      },
      async getPubkey() {
        try {
          this.checkoutDialog.data.pubkey = await window.nostr.getPublicKey()
          this.checkoutDialog.data.privkey = null
        } catch (err) {
          console.error(
            `Failed to get a public key from a Nostr extension: ${err}`
          )
        }
      },
      generateKeyPair() {
        let sk = NostrTools.generatePrivateKey()
        let pk = NostrTools.getPublicKey(sk)
        this.checkoutDialog.data.pubkey = pk
        this.checkoutDialog.data.privkey = sk
      },
      placeOrder() {
        LNbits.utils
          .confirmDialog(
            `Send the order to the merchant? You should receive a message with the payment details.`
          )
          .onOk(async () => {
            let orderData = this.checkoutDialog.data
            let content = {
              name: orderData?.username,
              description: null,
              address: orderData.address,
              message: null,
              contact: {
                nostr: orderData.pubkey,
                phone: null,
                email: orderData?.email
              },
              items: Array.from(this.cart.products, p => {
                return {product_id: p[0], quantity: p[1].quantity}
              })
            }
            let event = {
              kind: 4,
              created_at: Math.floor(Date.now() / 1000),
              tags: [],
              content: await window.nostr.nip04.encrypt(
                orderData.pubkey,
                content
              ),
              pubkey: orderData.pubkey
            }
            event.id = NostrTools.getEventHash(event)
            if (orderData.privkey) {
              event.sig = NostrTools.signEvent(event, orderData.privkey)
            } else if (this.hasNip07) {
              await window.nostr.signEvent(event)
            }
            await this.sendOrder(event)
          })
      },
      async sendOrder(order) {
        const pool = new NostrTools.SimplePool()
        let relays = Array.from(this.relays)
        let pubs = await pool.publish(relays, order)
        pubs.on('ok', relay => {
          console.log(`${relay.url} has accepted our event`)
        })
        pubs.on('failed', reason => {
          console.log(`failed to publish to ${reason}`)
        })
      }
    },
    created() {
      setTimeout(() => {
        if (window.nostr) {
          this.hasNip07 = true
        }
      }, 1000)
    }
  })
}
