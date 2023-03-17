async function customerStall(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: [
      'account',
      'stall',
      'products',
      'product-detail',
      'change-page',
      'relays'
    ],
    data: function () {
      return {
        loading: false,
        isPwd: true,
        cart: {
          total: 0,
          size: 0,
          products: new Map()
        },
        cartMenu: [],
        hasNip07: false,
        customerPubkey: null,
        customerPrivkey: null,
        customerUseExtension: null,
        activeOrder: null,
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
          dismissMsg: null,
          show: false
        },
        downloadOrderDialog: {
          show: false,
          data: {}
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
      },
      dropIn() {
        return {
          privkey: this.customerPrivkey,
          pubkey: this.customerPubkey,
          useExtension: this.customerUseExtension
        }
      }
    },
    methods: {
      changePageS(page, opts) {
        this.$emit('change-page', page, opts)
      },
      copyText: function (text) {
        var notify = this.$q.notify
        Quasar.utils.copyToClipboard(text).then(function () {
          notify({
            message: 'Copied to clipboard!',
            position: 'bottom'
          })
        })
      },
      getAmountFormated(amount, unit = 'USD') {
        return LNbits.utils.formatCurrency(amount, unit)
      },
      addToCart(item) {
        let prod = this.cart.products
        if (prod.has(item.id)) {
          let qty = prod.get(item.id).quantity
          if (qty == item.quantity) {
            this.$q.notify({
              type: 'warning',
              message: `${item.name} only has ${item.quantity} units!`,
              icon: 'production_quantity_limits'
            })
            return
          }
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
        this.$q.localStorage.set(`diagonAlley.carts.${this.stall.id}`, {
          ...this.cart,
          products: Object.fromEntries(this.cart.products)
        })
      },
      resetCart() {
        this.cart = {
          total: 0,
          size: 0,
          products: new Map()
        }
        this.$q.localStorage.remove(`diagonAlley.carts.${this.stall.id}`)
      },
      async downloadOrder() {
        let created_at = Math.floor(Date.now() / 1000)
        let orderData = this.checkoutDialog.data
        let orderObj = {
          name: orderData?.username,
          address: orderData.address,
          message: orderData?.message,
          contact: {
            nostr: orderData.pubkey,
            phone: null,
            email: orderData?.email
          },
          items: Array.from(this.cart.products, p => {
            return {product_id: p[0], quantity: p[1].quantity}
          })
        }
        orderObj.id = await hash(
          [orderData.pubkey, created_at, JSON.stringify(orderObj)].join(':')
        )
        this.downloadOrderDialog.data = orderObj
        this.downloadOrderDialog.show = true
        this.resetCheckout()
        this.resetCart()
      },
      async getFromExtension() {
        this.customerPubkey = await window.nostr.getPublicKey()
        this.customerUseExtension = true
        this.checkoutDialog.data.pubkey = this.customerPubkey
      },
      async generateKeyPair() {
        this.customerPrivkey = NostrTools.generatePrivateKey()
        this.customerPubkey = NostrTools.getPublicKey(this.customerPrivkey)
        this.customerUseExtension = false
        this.checkoutDialog.data.pubkey = this.customerPubkey
        this.checkoutDialog.data.privkey = this.customerPrivkey
      },
      openCheckout() {
        // Check if user is logged in
        if (this.customerPubkey) {
          this.checkoutDialog.data.pubkey = this.customerPubkey
          if (this.customerPrivkey && !this.useExtension) {
            this.checkoutDialog.data.privkey = this.customerPrivkey
          }
        }
        this.checkoutDialog.show = true
      },
      resetCheckout() {
        this.loading = false
        this.checkoutDialog = {
          show: false,
          data: {
            pubkey: null
          }
        }
      },
      openQrCodeDialog() {
        this.qrCodeDialog = {
          data: {
            payment_request: null
          },
          dismissMsg: null,
          show: false
        }
      },
      closeQrCodeDialog() {
        this.qrCodeDialog.show = false
        setTimeout(() => {
          this.qrCodeDialog.dismissMsg()
        }, 1000)
      },
      async placeOrder() {
        this.loading = true
        let orderData = this.checkoutDialog.data
        let orderObj = {
          name: orderData?.username,
          address: orderData.address,
          message: orderData?.message,
          contact: {
            nostr: this.customerPubkey,
            phone: null,
            email: orderData?.email
          },
          items: Array.from(this.cart.products, p => {
            return {product_id: p[0], quantity: p[1].quantity}
          })
        }
        let created_at = Math.floor(Date.now() / 1000)
        orderObj.id = await hash(
          [this.customerPubkey, created_at, JSON.stringify(orderObj)].join(':')
        )
        this.activeOrder = orderObj.id
        let event = {
          ...(await NostrTools.getBlankEvent()),
          kind: 4,
          created_at,
          tags: [['p', this.stall.pubkey]],
          pubkey: this.customerPubkey
        }
        if (this.customerPrivkey) {
          event.content = await NostrTools.nip04.encrypt(
            this.customerPrivkey,
            this.stall.pubkey,
            JSON.stringify(orderObj)
          )
        } else if (this.customerUseExtension && this.hasNip07) {
          event.content = await window.nostr.nip04.encrypt(
            this.stall.pubkey,
            JSON.stringify(orderObj)
          )
          let userRelays = Object.keys(
            (await window.nostr?.getRelays?.()) || []
          )
          if (userRelays.length != 0) {
            userRelays.map(r => this.relays.add(r))
          }
        }
        event.id = NostrTools.getEventHash(event)
        if (this.customerPrivkey) {
          event.sig = await NostrTools.signEvent(event, this.customerPrivkey)
        } else if (this.customerUseExtension && this.hasNip07) {
          event = await window.nostr.signEvent(event)
        }
        this.resetCheckout()
        await this.sendOrder(event)
      },
      async sendOrder(order) {
        this.$q.notify({
          message: 'Waiting for invoice from merchant...'
        })
        for (const url of Array.from(this.relays)) {
          try {
            let relay = NostrTools.relayInit(url)
            relay.on('connect', () => {
              console.debug(`connected to ${relay.url}`)
            })
            relay.on('error', () => {
              console.debug(`failed to connect to ${relay.url}`)
              relay.close()
              return
            })

            await relay.connect()
            let pub = relay.publish(order)
            pub.on('ok', () => {
              console.debug(`${relay.url} has accepted our event: ${order.id}`)
              relay.close()
            })
            pub.on('failed', reason => {
              console.debug(`failed to publish to ${relay.url}: ${reason}`)
              relay.close()
            })
          } catch (err) {
            console.error(`Error: ${err}`)
          }
        }
        this.loading = false
        this.resetCart()
        this.openQrCodeDialog()
        this.listenMessages()
      },
      async listenMessages() {
        this.loading = true
        try {
          const pool = new NostrTools.SimplePool()
          const filters = [
            {
              kinds: [4],
              authors: [this.stall.pubkey]
            },
            {
              kinds: [4],
              '#p': [this.customerPubkey]
            }
          ]
          let relays = Array.from(this.relays)
          let subs = pool.sub(relays, filters)
          subs.on('event', async event => {
            let mine = event.pubkey == this.customerPubkey
            let sender = mine
              ? event.tags.find(([k, v]) => k === 'p' && v && v !== '')[1]
              : event.pubkey
            try {
              let plaintext
              if (this.customerPrivkey) {
                plaintext = await NostrTools.nip04.decrypt(
                  this.customerPrivkey,
                  sender,
                  event.content
                )
              } else if (this.customerUseExtension && this.hasNip07) {
                plaintext = await window.nostr.nip04.decrypt(
                  sender,
                  event.content
                )
              }

              this.messageFilter(plaintext, cb => Promise.resolve(pool.close))
            } catch {
              console.debug('Unable to decrypt message! Probably not for us!')
            }
          })
        } catch (err) {
          console.error(`Error: ${err}`)
        }
      },
      messageFilter(text, cb = () => {}) {
        if (!isJson(text)) return
        let json = JSON.parse(text)
        if (json.id != this.activeOrder) return
        if (json.payment_options) {
          let payment_request = json.payment_options.find(o => o.type == 'ln')
            .link
          if (!payment_request) return
          this.loading = false
          this.qrCodeDialog.data.payment_request = payment_request
          this.qrCodeDialog.dismissMsg = this.$q.notify({
            timeout: 0,
            message: 'Waiting for payment...'
          })
        } else if (json.paid) {
          this.closeQrCodeDialog()
          this.$q.notify({
            type: 'positive',
            message: 'Sats received, thanks!',
            icon: 'thumb_up'
          })
          this.activeOrder = null
          Promise.resolve(cb())
        } else {
          return
        }
      }
    },
    created() {
      this.customerPubkey = this.account?.pubkey
      this.customerPrivkey = this.account?.privkey
      this.customerUseExtension = this.account?.useExtension
      let storedCart = this.$q.localStorage.getItem(
        `diagonAlley.carts.${this.stall.id}`
      )
      if (storedCart) {
        this.cart.total = storedCart.total
        this.cart.size = storedCart.size
        this.cart.products = new Map(Object.entries(storedCart.products))

        this.cartMenu = Array.from(this.cart.products, item => {
          return {id: item[0], ...item[1]}
        })
      }
      setTimeout(() => {
        if (window.nostr) {
          this.hasNip07 = true
        }
      }, 1000)
    }
  })
}
