const market = async () => {
  Vue.component(VueQrcode.name, VueQrcode)

  const NostrTools = window.NostrTools

  const defaultRelays = [
    'wss://relay.damus.io',
    'wss://relay.snort.social',
    'wss://nostr-pub.wellorder.net',
    'wss://nostr.zebedee.cloud'
  ]
  const eventToObj = event => {
    event.content = JSON.parse(event.content) || null

    return {
      ...event,
      ...Object.values(event.tags).reduce((acc, tag) => {
        let [key, value] = tag
        if (key == 't') {
          return { ...acc, [key]: [...(acc[key] || []), value] }
        } else {
          return { ...acc, [key]: value }
        }
      }, {})
    }
  }
  await Promise.all([
    productCard('static/components/product-card/product-card.html'),
    customerMarket('static/components/customer-market/customer-market.html'),
    customerStall('static/components/customer-stall/customer-stall.html'),
    productDetail('static/components/product-detail/product-detail.html'),
    shoppingCart('static/components/shopping-cart/shopping-cart.html'),
    shoppingCartList('static/components/shopping-cart-list/shopping-cart-list.html'),
    shoppingCartCheckout('static/components/shopping-cart-checkout/shopping-cart-checkout.html'),
    customerOrders('static/components/customer-orders/customer-orders.html'),
    chatDialog('static/components/chat-dialog/chat-dialog.html'),
    marketConfig('static/components/market-config/market-config.html')
  ])

  new Vue({
    el: '#vue',
    mixins: [windowMixin],
    data: function () {
      return {
        account: null,
        accountMetadata: null,
        accountDialog: {
          show: false,
          data: {
            watchOnly: false,
            key: null
          }
        },

        merchants: [],
        shoppingCarts: [],
        checkoutCart: null,
        checkoutStall: null,

        activePage: 'market',
        activeOrderId: null,
        dmSubscriptions: {},

        qrCodeDialog: {
          data: {
            payment_request: null
          },
          dismissMsg: null,
          show: false
        },

        searchNostr: false,
        drawer: true,
        pubkeys: new Set(),
        relays: new Set(),
        events: [],
        stalls: [],
        products: [],
        profiles: new Map(),
        searchText: null,
        inputPubkey: null,
        inputRelay: null,
        activePage: 'market',
        activeStall: null,
        activeProduct: null,
        pool: null,
        config: null,
        configDialog: {
          show: false,
          data: {
            name: null,
            about: null,
            ui: {
              picture: null,
              banner: null,
              theme: null
            }
          }
        },
        naddr: null,
        loading: false
      }
    },
    computed: {
      allOrders() {
        const prefix = 'nostrmarket.orders.'
        const orderKeys = this.$q.localStorage.getAllKeys().filter(k => k.startsWith(prefix))

        return orderKeys.map((key) => ({
          pubkey: key.substring(prefix.length),
          orders: this.$q.localStorage.getItem(key)
        }), {})
      },
      filterProducts() {
        let products = this.products
        console.log('### this.products', this.products)
        if (this.activeStall) {
          products = products.filter(p => p.stall_id == this.activeStall)
        }
        if (!this.searchText || this.searchText.length < 2) return products
        const searchText = this.searchText.toLowerCase()
        return products.filter(p => {
          return (
            p.name.toLowerCase().includes(searchText) ||
            (p.description &&
              p.description.toLowerCase().includes(searchText)) ||
            (p.categories &&
              p.categories.toString().toLowerCase().includes(searchText))
          )
        })
      },
      stallName() {
        return this.stalls.find(s => s.id == this.activeStall)?.name || 'Stall'
      },
      productName() {
        return (
          this.products.find(p => p.id == this.activeProduct)?.name || 'Product'
        )
      },
      isLoading() {
        return this.$q.loading.isActive
      },
      hasExtension() {
        return window.nostr
      },
      isValidAccountKey() {
        return isValidKey(this.accountDialog.data.key)
      },
      canEditConfig() {
        return this.account && this.account.pubkey == this.config?.pubkey
      },

      allCartsItemCount() {
        return this.shoppingCarts.map(s => s.products).flat().reduce((t, p) => t + p.orderedQuantity, 0)
      }
    },
    async created() {
      this.merchants = this.$q.localStorage.getItem('nostrmarket.merchants') || []
      this.shoppingCarts = this.$q.localStorage.getItem('nostrmarket.shoppingCarts') || []

      this.account = this.$q.localStorage.getItem('nostrmarket.account') || null



      //console.log("UUID", crypto.randomUUID())

      // Check for stored merchants and relays on localStorage
      try {
        let merchants = this.$q.localStorage.getItem(`diagonAlley.merchants`)
        let relays = this.$q.localStorage.getItem(`diagonAlley.relays`)
        if (merchants && merchants.length) {
          this.pubkeys = new Set(merchants)
        }
        if (this.account) {
          this.pubkeys.add(this.account.pubkey)
        }
        if (relays && relays.length) {
          this.relays = new Set(relays)
        } else {
          this.relays = new Set(defaultRelays)
        }
      } catch (e) {
        console.error(e)
      }

      let params = new URLSearchParams(window.location.search)
      let merchant_pubkey = params.get('merchant_pubkey')
      let stall_id = params.get('stall_id')
      let product_id = params.get('product_id')
      let naddr = params.get('naddr')

      if (naddr) {
        try {
          let { type, data } = NostrTools.nip19.decode(naddr)
          if (type == 'naddr' && data.kind == '30019') { // just double check
            this.config = {
              d: data.identifier,
              pubkey: data.pubkey,
              relays: data.relays
            }
          }
          this.naddr = naddr
        } catch (err) {
          console.error(err)
        }
      }

      // What component to render on start
      if (stall_id) {
        if (product_id) {
          this.activeProduct = product_id
        }
        this.activePage = 'stall'
        this.activeStall = stall_id
      }
      if (merchant_pubkey && !this.pubkeys.has(merchant_pubkey)) {
        await LNbits.utils
          .confirmDialog(
            `We found a merchant pubkey in your request. Do you want to add it to the merchants list?`
          )
          .onOk(async () => {
            await this.addPubkey(merchant_pubkey)
          })
      }

      // Get notes from Nostr
      await this.initNostr()

      this.$q.loading.hide()


      await this.listenForIncommingDms(this.merchants.map(m => ({ publicKey: m.publicKey, since: this.lastDmForPubkey(m.publicKey) })))
    },
    methods: {
      async deleteAccount() {
        await LNbits.utils
          .confirmDialog(
            `This will delete all stored data. If you didn't backup the Key Pair (Private and Public Keys), you will lose it. Continue?`
          )
          .onOk(() => {
            window.localStorage.removeItem('nostrmarket.account')
            this.account = null
          })
      },
      async createAccount(useExtension = false) {
        console.log('### createAccount',)
        let nip07
        if (useExtension) {
          await this.getFromExtension()
          nip07 = true
        }
        if (isValidKey(this.accountDialog.data.key, 'nsec')) {
          let { key, watchOnly } = this.accountDialog.data
          if (key.startsWith('n')) {
            let { type, data } = NostrTools.nip19.decode(key)
            key = data
          }
          this.$q.localStorage.set('nostrmarket.account', {
            privkey: watchOnly ? null : key,
            pubkey: watchOnly ? key : NostrTools.getPublicKey(key),
            useExtension: nip07 ?? false
          })
          this.accountDialog.data = {
            watchOnly: false,
            key: null
          }
          this.accountDialog.show = false
          this.account = this.$q.localStorage.getItem('nostrmarket.account')
        }
        this.accountDialog.show = false
      },
      generateKeyPair() {
        this.accountDialog.data.key = NostrTools.generatePrivateKey()
        this.accountDialog.data.watchOnly = false
      },
      async getFromExtension() {
        this.accountDialog.data.key = await window.nostr.getPublicKey()
        this.accountDialog.data.watchOnly = true
        return
      },
      openAccountDialog() {
        this.accountDialog.show = true
      },
      editConfigDialog() {
        if (this.canEditConfig && this.config?.opts) {
          let { name, about, ui } = this.config.opts
          this.configDialog.data = { name, about, ui }
          this.configDialog.data.identifier = this.config?.d
        }
        this.openConfigDialog()
      },
      openConfigDialog() {
        if (!this.account) {
          this.$q.notify({
            message: `You need to be logged in first.`,
            color: 'negative',
            icon: 'warning'
          })
          return
        }
        this.configDialog.show = true
      },
      async sendConfig() {
        let { name, about, ui } = this.configDialog.data
        let merchants = Array.from(this.pubkeys)
        let identifier = this.configDialog.data.identifier ?? crypto.randomUUID()
        let event = {
          ...(await NostrTools.getBlankEvent()),
          kind: 30019,
          content: JSON.stringify({ name, about, ui, merchants }),
          created_at: Math.floor(Date.now() / 1000),
          tags: [['d', identifier]],
          pubkey: this.account.pubkey
        }
        event.id = NostrTools.getEventHash(event)
        try {
          if (this.account.useExtension) {
            event = await window.nostr.signEvent(event)
          } else if (this.account.privkey) {
            event.sig = await NostrTools.signEvent(event, this.account.privkey)
          }
          let pub = this.pool.publish(Array.from(this.relays), event)
          pub.on('ok', () => console.debug(`Config event was sent`))
          pub.on('failed', error => console.error(error))
        } catch (err) {
          console.error(err)
          this.$q.notify({
            message: `Error signing event.`,
            color: 'negative',
            icon: 'warning'
          })
          return
        }
        this.naddr = NostrTools.nip19.naddrEncode({
          pubkey: event.pubkey,
          kind: 30019,
          identifier: identifier,
          relays: Array.from(this.relays)
        })
        this.config = this.configDialog.data
        this.resetConfig()
        return
      },
      resetConfig() {
        this.configDialog = {
          show: false,
          identifier: null,
          data: {
            name: null,
            about: null,
            ui: {
              picture: null,
              banner: null,
              theme: null
            }
          }
        }
      },
      async updateData(events) {
        console.log('### updateData', events)
        if (events.length < 1) {
          this.$q.notify({
            message: 'No matches were found!'
          })
          return
        }
        let products = new Map()
        let stalls = new Map()

        this.stalls.forEach(s => stalls.set(s.id, s))
        this.products.forEach(p => products.set(p.id, p))

        events.map(eventToObj).map(e => {
          if (e.kind == 0) {
            this.profiles.set(e.pubkey, e.content)
            if (e.pubkey == this.account?.pubkey) {
              this.accountMetadata = this.profiles.get(this.account.pubkey)
            }
            this.merchants.filter(m => m.publicKey === e.pubkey).forEach(m => m.profile = e.content)
            console.log('### this.merchants', this.merchants)
            return
          } else if (e.kind == 30018) {
            //it's a product `d` is the prod. id
            products.set(e.d, { ...e.content, pubkey: e.pubkey, id: e.d, categories: e.t })
          } else if (e.kind == 30017) {
            // it's a stall `d` is the stall id
            stalls.set(e.d, { ...e.content, pubkey: e.pubkey, id: e.d, pubkey: e.pubkey })
          }
        })

        this.stalls = await Array.from(stalls.values())

        this.products = Array.from(products.values())
          .map(obj => {
            let stall = this.stalls.find(s => s.id == obj.stall_id)
            if (!stall) return
            obj.stallName = stall.name
            obj.images = obj.images || [obj.image]
            if (obj.currency != 'sat') {
              obj.formatedPrice = this.getAmountFormated(
                obj.price,
                obj.currency
              )
            }
            return obj
          })
          .filter(f => f)
      },
      async initNostr() {
        this.$q.loading.show()
        const pool = new NostrTools.SimplePool()

        // If there is an naddr in the URL, get it and parse content
        if (this.config) {
          // add relays to the set   
          this.config.relays.forEach(r => this.relays.add(r))
          await pool.get(this.config.relays, {
            kinds: [30019],
            limit: 1,
            authors: [this.config.pubkey],
            '#d': [this.config.d]
          }).then(event => {
            if (!event) return
            let content = JSON.parse(event.content)
            this.config = { ... this.config, opts: content }
            // add merchants 
            this.config.opts?.merchants.forEach(m => this.pubkeys.add(m))
            // change theme
            let { theme } = this.config.opts?.ui
            theme && document.body.setAttribute('data-theme', theme)
          }).catch(err => console.error(err))
        }

        let relays = Array.from(this.relays)

        const authors = Array.from(this.pubkeys).concat(this.merchants.map(m => m.publicKey))
        console.log('### stupid', authors)
        // Get metadata and market data from the pubkeys
        await pool
          .list(relays, [
            {
              kinds: [0, 30017, 30018], // for production kind is 30017
              authors
            }
          ])
          .then(async events => {
            console.log('### stupid response', events)
            if (!events || events.length == 0) return
            await this.updateData(events)
          })

        this.$q.loading.hide()
        this.pool = pool
        this.poolSubscribe()
        return
      },
      async poolSubscribe() {
        const authors = Array.from(this.pubkeys).concat(this.merchants.map(m => m.publicKey))
        console.log('### poolSubscribe.authors', authors)
        this.poolSub = this.pool.sub(Array.from(this.relays), [
          {
            kinds: [0, 30017, 30018],
            authors,
            since: Date.now() / 1000
          }
        ])
        this.poolSub.on(
          'event',
          event => {
            this.updateData([event])
          },
          { id: 'masterSub' } //pass ID to cancel previous sub
        )
      },
      navigateTo(page, opts = { stall: null, product: null, pubkey: null }) {
        console.log("### navigateTo", page, opts)
        let { stall, product, pubkey } = opts
        let url = new URL(window.location)

        if (pubkey) url.searchParams.set('merchant_pubkey', pubkey)
        if (stall && !pubkey) {
          pubkey = this.stalls.find(s => s.id == stall).pubkey
          url.searchParams.set('merchant_pubkey', pubkey)
        }

        if (page === 'stall' || page === 'product') {
          if (stall) {
            this.activeStall = stall
            url.searchParams.set('stall_id', stall)

            this.activeProduct = product
            if (product) {
              url.searchParams.set('product_id', product)
            }
          }
        } else {
          this.activeStall = null
          this.activeProduct = null

          url.searchParams.delete('merchant_pubkey')
          url.searchParams.delete('stall_id')
          url.searchParams.delete('product_id')

          this.setActivePage('market')
        }

        window.history.pushState({}, '', url)
        this.activePage = page
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
      async addPubkey(pubkey) {
        if (!pubkey) {
          pubkey = String(this.inputPubkey).trim()
        }
        let regExp = /^#([0-9a-f]{3}){1,2}$/i
        if (pubkey.startsWith('n')) {
          try {
            let { type, data } = NostrTools.nip19.decode(pubkey)
            if (type === 'npub') pubkey = data
            else if (type === 'nprofile') {
              pubkey = data.pubkey
              givenRelays = data.relays
            }
          } catch (err) {
            console.error(err)
          }
        } else if (regExp.test(pubkey)) {
          pubkey = pubkey
        }
        this.pubkeys.add(pubkey)
        this.inputPubkey = null
        this.$q.localStorage.set(
          `diagonAlley.merchants`,
          Array.from(this.pubkeys)
        )
        this.initNostr()
      },
      removePubkey(pubkey) {
        // Needs a hack for Vue reactivity
        let pubkeys = this.pubkeys
        pubkeys.delete(pubkey)
        this.profiles.delete(pubkey)
        this.pubkeys = new Set(Array.from(pubkeys))
        this.$q.localStorage.set(
          `diagonAlley.merchants`,
          Array.from(this.pubkeys)
        )
        this.initNostr()
      },
      async addRelay() {
        let relay = String(this.inputRelay).trim()
        if (!relay.startsWith('ws')) {
          console.debug('invalid url')
          return
        }
        this.relays.add(relay)
        this.$q.localStorage.set(`diagonAlley.relays`, Array.from(this.relays))
        this.inputRelay = null
        this.initNostr()
      },
      removeRelay(relay) {
        // Needs a hack for Vue reactivity
        let relays = this.relays
        relays.delete(relay)
        this.relays = new Set(Array.from(relays))
        this.$q.localStorage.set(`diagonAlley.relays`, Array.from(this.relays))
        this.initNostr()
      },

      setActivePage(page = 'market') {
        this.activePage = page
      },

      addMerchant(publicKey) {
        console.log('### addMerchat', publicKey)

        this.merchants.unshift({
          publicKey,
          profile: null
        })
        this.$q.localStorage.set('nostrmarket.merchants', this.merchants)
        this.initNostr() // todo: improve
      },
      removeMerchant(publicKey) {
        console.log('### removeMerchat', publicKey)
        this.merchants = this.merchants.filter(m => m.publicKey !== publicKey)
        this.$q.localStorage.set('nostrmarket.merchants', this.merchants)
        this.products = this.products.filter(p => p.pubkey !== publicKey)
        this.stalls = this.stalls.filter(p => p.pubkey !== publicKey)
        this.initNostr() // todo: improve
      },

      addProductToCart(item) {
        let stallCart = this.shoppingCarts.find(s => s.id === item.stall_id)
        if (!stallCart) {
          stallCart = {
            id: item.stall_id,
            products: []
          }
          this.shoppingCarts.push(stallCart)
        }
        stallCart.merchant = this.merchants.find(m => m.publicKey === item.pubkey)

        let product = stallCart.products.find(p => p.id === item.id)
        if (!product) {
          product = { ...item, orderedQuantity: 0 }
          stallCart.products.push(product)

        }
        product.orderedQuantity = Math.min(product.quantity, item.orderedQuantity || (product.orderedQuantity + 1))

        this.$q.localStorage.set('nostrmarket.shoppingCarts', this.shoppingCarts)
      },

      removeProductFromCart(item) {
        const stallCart = this.shoppingCarts.find(c => c.id === item.stallId)
        if (stallCart) {
          stallCart.products = stallCart.products.filter(p => p.id !== item.productId)
          if (!stallCart.products.length) {
            this.shoppingCarts = this.shoppingCarts.filter(s => s.id !== item.stallId)
          }
          this.$q.localStorage.set('nostrmarket.shoppingCarts', this.shoppingCarts)
        }
      },
      removeCart(stallId) {
        this.shoppingCarts = this.shoppingCarts.filter(s => s.id !== stallId)
        this.$q.localStorage.set('nostrmarket.shoppingCarts', this.shoppingCarts)
      },

      checkoutStallCart(cart) {
        this.checkoutCart = cart
        this.checkoutStall = this.stalls.find(s => s.id === cart.id)
        this.setActivePage('shopping-cart-checkout')
      },

      async placeOrder({ event, order }) {
        if (!this.account.privkey) {
          this.openAccountDialog()
          return
        }
        this.activeOrderId = order.id
        event.content = await NostrTools.nip04.encrypt(
          this.account.privkey,
          this.checkoutStall.pubkey,
          JSON.stringify(order)
        )

        event.id = NostrTools.getEventHash(event)
        event.sig = await NostrTools.signEvent(event, this.account.privkey)

        this.sendOrderEvent(event)
        this.persistOrderUpdate(this.checkoutStall.pubkey, order)
      },

      sendOrderEvent(event) {
        const pub = this.pool.publish(Array.from(this.relays), event)
        this.$q.notify({
          type: 'positive',
          message: 'The order has been placed!'
        })
        this.qrCodeDialog = {
          data: {
            payment_request: null
          },
          dismissMsg: null,
          show: true
        }
        pub.on('ok', () => {
          this.qrCodeDialog.show = true
        })
        pub.on('failed', (error) => {
          // do not show to user. It is possible that only one relay has failed
          console.error(error)
        })
      },

      async listenForIncommingDms(from) {
        console.log('### from', from)
        if (!this.account?.privkey) {
          this.$q.notify({
            message: 'Cannot listen for direct messages. You need to login first!',
            icon: 'warning'
          })
          return
        }

        try {
          const filters = from.map(f =>
          ({
            kinds: [4],
            authors: [f.publicKey],
            '#p': [this.account.pubkey],
            since: f.since
          }))

          console.log('### filters', filters)
          const subs = this.pool.sub(Array.from(this.relays), filters)
          subs.on('event', async event => {
            const receiverPubkey = event.tags.find(([k, v]) => k === 'p' && v && v !== '')[1]
            if (receiverPubkey !== this.account.pubkey) {
              console.log('Unexpected DM. Dropped!')
              return
            }
            await this.handleIncommingDm(event)
          })
          return subs
        } catch (err) {
          console.error(`Error: ${err}`)
        }
      },
      async handleIncommingDm(event) {
        this.persistDMEvent(event)
        try {
          const plainText = await NostrTools.nip04.decrypt(
            this.account.privkey,
            event.pubkey,
            event.content
          )
          console.log('### plainText', plainText)
          if (!isJson(plainText)) return

          const jsonData = JSON.parse(plainText)
          if (jsonData.type === 1) {
            this.handlePaymentRequest(jsonData)
            this.persistOrderUpdate(event.pubkey, jsonData)
          } else if (jsonData.type === 2) {
            this.handleOrderStatusUpdate(jsonData)
            this.persistOrderUpdate(event.pubkey, jsonData)
          }
        } catch (e) {
          console.warn('Unable to handle incomming DM', e)
        }
      },

      handlePaymentRequest(json) {
        if (!json.payment_options?.length) {
          this.qrCodeDialog.data.message = json.message || 'Unexpected error'
          return
        }
        if (json.id && (json.id !== this.activeOrderId)) {
          // not for active order, store somewehre else
          return
        }
        let paymentRequest = json.payment_options.find(o => o.type == 'ln')
          .link
        if (!paymentRequest) return
        this.qrCodeDialog.data.payment_request = paymentRequest
        this.qrCodeDialog.dismissMsg = this.$q.notify({
          timeout: 0,
          message: 'Waiting for payment...'
        })

      },

      handleOrderStatusUpdate(jsonData) {
        if (this.qrCodeDialog.dismissMsg) {
          this.qrCodeDialog.dismissMsg()
          this.qrCodeDialog.show = false
        }
        const message = jsonData.shipped ? 'Order shipped' : jsonData.paid ? 'Order paid' : 'Order notification'
        this.$q.notify({
          type: 'positive',
          message: message,
          caption: jsonData.message || ''
        })
      },

      persistDMEvent(event) {
        const dms = this.$q.localStorage.getItem(`nostrmarket.dm.${event.pubkey}`) || { events: [], lastCreatedAt: 0 }
        const existingEvent = dms.events.find(e => e.id === event.id)
        if (existingEvent) return

        dms.events.push(event)
        dms.events.sort((a, b) => a - b)
        dms.lastCreatedAt = dms.events[dms.events.length - 1].created_at
        console.log('### dms', dms)
        this.$q.localStorage.set(`nostrmarket.dm.${event.pubkey}`, dms)
      },

      lastDmForPubkey(pubkey) {
        const dms = this.$q.localStorage.getItem(`nostrmarket.dm.${pubkey}`)
        if (!dms) return 0
        return dms.lastCreatedAt
      },

      persistOrderUpdate(pubkey, orderUpdate) {
        console.log('### persistOrderUpdate', pubkey, orderUpdate)
        const orders = this.$q.localStorage.getItem(`nostrmarket.orders.${pubkey}`) || []
        let order = orders.find(o => o.id === orderUpdate.id)
        if (!order) {
          orders.push({ ...orderUpdate, messages: orderUpdate.message ? [orderUpdate.message] : [] })
          this.$q.localStorage.set(`nostrmarket.orders.${pubkey}`, orders)
          return
        }

        if (orderUpdate.message) {
          order.messages.push(orderUpdate.message)
        }

        if (orderUpdate.type === 0 || orderUpdate.type === 1) {
          order = { ...orderUpdate, ...order }
        } else if (orderUpdate.type === 2) {
          order.paid = orderUpdate.paid
          order.shipped = orderUpdate.shipped
        }

        this.$q.localStorage.set(`nostrmarket.orders.${pubkey}`, [order].concat(orders.filter(o => o.id !== order.id)))
      }

    }
  })
}

market()
