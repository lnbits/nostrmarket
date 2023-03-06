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
        customerPubkey: null,
        customerPrivKey: null,
        nostrMessages: new Map(),
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
      resetCheckout() {
        this.checkoutDialog = {
          show: false,
          data: {
            pubkey: null
          }
        }
      },
      async getPubkey() {
        try {
          this.customerPubkey = await window.nostr.getPublicKey()
          this.checkoutDialog.data.pubkey = this.customerPubkey
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
        this.customerPubkey = pk
        this.customerPrivKey = sk
        this.checkoutDialog.data.pubkey = this.customerPubkey
        this.checkoutDialog.data.privkey = this.customerPrivKey
      },
      async placeOrder() {
        LNbits.utils
          .confirmDialog(
            `Send the order to the merchant? You should receive a message with the payment details.`
          )
          .onOk(async () => {
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
              [this.customerPubkey, created_at, JSON.stringify(orderObj)].join(
                ':'
              )
            )
            let event = {
              ...(await NostrTools.getBlankEvent()),
              kind: 4,
              created_at,
              tags: [['p', this.stall.pubkey]],
              pubkey: this.customerPubkey
            }
            if (this.customerPrivKey) {
              event.content = await NostrTools.nip04.encrypt(
                this.customerPrivKey,
                this.stall.pubkey,
                JSON.stringify(orderObj)
              )
            } else {
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
            if (this.customerPrivKey) {
              event.sig = await NostrTools.signEvent(
                event,
                this.customerPrivKey
              )
            } else if (this.hasNip07) {
              event = await window.nostr.signEvent(event)
            }
            console.log(event, orderObj)
            await this.sendOrder(event)
          })
      },
      async sendOrder(order) {
        for (const url of Array.from(this.relays)) {
          try {
            let relay = NostrTools.relayInit(url)
            relay.on('connect', () => {
              console.log(`connected to ${relay.url}`)
            })
            relay.on('error', () => {
              console.log(`failed to connect to ${relay.url}`)
            })

            await relay.connect()
            let pub = relay.publish(order)
            pub.on('ok', () => {
              console.log(`${relay.url} has accepted our event`)
            })
            pub.on('failed', reason => {
              console.log(`failed to publish to ${relay.url}: ${reason}`)
            })
          } catch (err) {
            console.error(`Error: ${err}`)
          }
        }
        this.resetCheckout()
        this.listenMessages()
      },
      async listenMessages() {
        try {
          const pool = new NostrTools.SimplePool()
          const filters = [
            {
              kinds: [4],
              authors: [this.customerPubkey]
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
            if (
              (mine && sender != this.stall.pubkey) ||
              (!mine && sender != this.customerPubkey)
            ) {
              console.log(`Not relevant message!`)
              return
            }
            try {
              let plaintext = this.customerPrivKey
                ? await NostrTools.nip04.decrypt(
                    this.customerPrivKey,
                    sender,
                    event.content
                  )
                : await window.nostr.nip04.decrypt(sender, event.content)
              // console.log(`${mine ? 'Me' : 'Customer'}: ${plaintext}`)
              this.nostrMessages.set(event.id, {
                msg: plaintext,
                timestamp: event.created_at,
                sender: `${mine ? 'Me' : 'Merchant'}`
              })
            } catch {
              console.error('Unable to decrypt message!')
              return
            }
          })
        } catch (err) {
          console.error(`Error: ${err}`)
        }
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
