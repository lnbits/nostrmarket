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
      closeQrCodeDialog() {
        this.qrCodeDialog.dismissMsg()
        this.qrCodeDialog.show = false
      },
      async placeOrder() {
        this.loading = true
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
              event.sig = await NostrTools.signEvent(
                event,
                this.customerPrivkey
              )
            } else if (this.customerUseExtension && this.hasNip07) {
              event = await window.nostr.signEvent(event)
            }

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
              relay.close()
            })
            pub.on('failed', reason => {
              console.log(`failed to publish to ${relay.url}: ${reason}`)
              relay.close()
            })
          } catch (err) {
            console.error(`Error: ${err}`)
          }
        }
        this.loading = false
        this.resetCheckout()
        this.resetCart()
        this.qrCodeDialog.show = true
        this.qrCodeDialog.dismissMsg = this.$q.notify({
          timeout: 0,
          message: 'Waiting for invoice from merchant...'
        })
        this.listenMessages()
      },
      async listenMessages() {
        console.log('LISTEN')
        try {
          const pool = new NostrTools.SimplePool()
          const filters = [
            // /
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
              console.log(`${mine ? 'Me' : 'Merchant'}: ${plaintext}`)

              // this.nostrMessages.set(event.id, {
              //   msg: plaintext,
              //   timestamp: event.created_at,
              //   sender: `${mine ? 'Me' : 'Merchant'}`
              // })
              this.messageFilter(plaintext, cb => Promise.resolve(pool.close))
            } catch {
              console.error('Unable to decrypt message!')
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
        if (json?.payment_options) {
          // this.qrCodeDialog.show = true
          this.qrCodeDialog.data.payment_request = json.payment_options.find(
            o => o.type == 'ln'
          ).link
          this.qrCodeDialog.dismissMsg = this.$q.notify({
            timeout: 0,
            message: 'Waiting for payment...'
          })
        } else if (json?.paid) {
          this.qrCodeDialog.dismissMsg = this.$q.notify({
            type: 'positive',
            message: 'Sats received, thanks!',
            icon: 'thumb_up'
          })
          this.closeQrCodeDialog()
          this.activeOrder = null
          Promise.resolve(cb())
        } else {
          return
        }
      }
      // async mockInit() {
      //   this.customerPubkey = await window.nostr.getPublicKey()
      //   this.activeOrder =
      //     'e4a16aa0198022dc682b2b52ed15767438282c0e712f510332fc047eaf795313'
      //   await this.listenMessages()
      // }
    },
    created() {
      this.customerPubkey = this.account.pubkey
      this.customerPrivkey = this.account.privkey
      this.customerUseExtension = this.account.useExtension
      setTimeout(() => {
        if (window.nostr) {
          this.hasNip07 = true
        }
      }, 1000)
    }
  })
}
