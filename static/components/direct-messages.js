window.app.component('direct-messages', {
  name: 'direct-messages',
  props: ['active-chat-customer', 'merchant-id', 'adminkey', 'inkey'],
  template: '#direct-messages',
  delimiters: ['${', '}'],
  watch: {
    activeChatCustomer: async function (n) {
      this.activePublicKey = n
    },
    activePublicKey: async function (n) {
      await this.getDirectMessages(n)
    }
  },
  computed: {
    messagesAsJson: function () {
      return this.messages.map(m => {
        const dateFrom = moment(m.event_created_at * 1000).fromNow()
        try {
          const message = JSON.parse(m.message)
          return {
            isJson: message.type >= 0,
            dateFrom,
            ...m,
            message
          }
        } catch (error) {
          return {
            isJson: false,
            dateFrom,
            ...m,
            message: m.message
          }
        }
      })
    },
    totalUnreadMessages: function () {
      return this.customers.reduce(
        (sum, c) => sum + (c.unread_messages || 0),
        0
      )
    },
    sortedCustomers: function () {
      return [...this.customers].sort((a, b) => {
        // First sort by unread messages (descending)
        if (a.unread_messages && !b.unread_messages) return -1
        if (!a.unread_messages && b.unread_messages) return 1
        // Then by name
        const nameA = (a.profile.name || '').toLowerCase()
        const nameB = (b.profile.name || '').toLowerCase()
        return nameA.localeCompare(nameB)
      })
    },
    activeCustomer: function () {
      if (!this.activePublicKey) return null
      return this.customers.find(c => c.public_key === this.activePublicKey)
    }
  },
  data: function () {
    return {
      customers: [],
      activePublicKey: null,
      messages: [],
      newMessage: '',
      showAddPublicKey: false,
      newPublicKey: null,
      showRawMessage: false,
      rawMessage: null
    }
  },
  methods: {
    sendMessage: async function () {},
    buildCustomerLabel: function (c) {
      if (!c) return ''
      let label = c.profile.name || 'unknown'
      if (c.profile.about) {
        label += ` - ${c.profile.about.substring(0, 30)}`
        if (c.profile.about.length > 30) label += '...'
      }
      if (c.unread_messages) {
        label = `[${c.unread_messages} new] ${label}`
      }
      label += ` (${c.public_key.slice(0, 8)}...${c.public_key.slice(-8)})`
      return label
    },
    truncateNpub: function (pubkey) {
      if (!pubkey) return ''
      return `${pubkey.slice(0, 8)}...${pubkey.slice(-8)}`
    },
    getIdenticonStyle: function (pubkey) {
      if (!pubkey) return {backgroundColor: '#666', borderRadius: '50%'}
      // Generate a color based on the pubkey (hex string)
      const hash = pubkey.slice(0, 6)
      const hue = parseInt(hash, 16) % 360 || 0
      return {
        backgroundColor: `hsl(${hue}, 65%, 45%)`,
        width: '100%',
        height: '100%',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }
    },
    handleAvatarError: function (event, customer) {
      // If avatar fails to load, mark it as failed to show identicon
      // Use Vue.set for reactivity or modify the profile object
      const index = this.customers.findIndex(
        c => c.public_key === customer.public_key
      )
      if (index !== -1) {
        this.customers[index].profile = {
          ...this.customers[index].profile,
          picture: null
        }
      }
    },
    selectCustomer: async function (pubkey) {
      this.activePublicKey = pubkey
      // Mark as read when selected
      const customer = this.customers.find(c => c.public_key === pubkey)
      if (customer && customer.unread_messages) {
        customer.unread_messages = 0
      }
    },
    getDirectMessages: async function (pubkey) {
      if (!pubkey) {
        this.messages = []
        return
      }
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/message/' + pubkey,
          this.inkey
        )
        this.messages = data

        this.focusOnChatBox(this.messages.length - 1)
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getCustomers: async function () {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          '/nostrmarket/api/v1/customer',
          this.inkey
        )
        // Ensure profile exists and add lastMessage property
        this.customers = data.map(c => ({
          ...c,
          profile: c.profile || {
            name: null,
            about: null,
            picture: null,
            nip05: null
          },
          lastMessage: null
        }))
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    getLastMessages: async function () {
      // Fetch last message for each customer for preview
      for (const customer of this.customers) {
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/message/' + customer.public_key + '?limit=1',
            this.inkey
          )
          if (data && data.length > 0) {
            const lastMsg = data[data.length - 1]
            try {
              const parsed = JSON.parse(lastMsg.message)
              customer.lastMessage = parsed.message || 'Order update'
            } catch {
              customer.lastMessage = lastMsg.message
            }
            if (customer.lastMessage && customer.lastMessage.length > 30) {
              customer.lastMessage =
                customer.lastMessage.substring(0, 30) + '...'
            }
          }
        } catch (error) {
          // Silently fail for individual customer message fetch
        }
      }
    },
    sendDirectMesage: async function () {
      try {
        const {data} = await LNbits.api.request(
          'POST',
          '/nostrmarket/api/v1/message',
          this.adminkey,
          {
            message: this.newMessage,
            public_key: this.activePublicKey
          }
        )
        this.messages = this.messages.concat([data])
        this.newMessage = ''
        this.focusOnChatBox(this.messages.length - 1)
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    addPublicKey: async function () {
      try {
        const {data} = await LNbits.api.request(
          'POST',
          '/nostrmarket/api/v1/customer',
          this.adminkey,
          {
            public_key: this.newPublicKey,
            merchant_id: this.merchantId,
            unread_messages: 0
          }
        )
        this.newPublicKey = null
        this.customers.push({
          ...data,
          lastMessage: null
        })
        this.activePublicKey = data.public_key
        await this.selectCustomer(data.public_key)
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.showAddPublicKey = false
      }
    },
    handleNewMessage: async function (data) {
      if (data.customerPubkey === this.activePublicKey) {
        this.messages.push(data.dm)
        this.focusOnChatBox(this.messages.length - 1)
      }
      this.getCustomersDebounced()
    },
    showOrderDetails: function (orderId, eventId) {
      this.$emit('order-selected', {orderId, eventId})
    },
    showClientOrders: function () {
      this.$emit('customer-selected', this.activePublicKey)
    },
    selectActiveCustomer: async function () {
      await this.getDirectMessages(this.activePublicKey)
      await this.getCustomers()
    },
    showMessageRawData: function (index) {
      this.rawMessage = this.messages[index]?.message
      this.showRawMessage = true
    },
    focusOnChatBox: function (index) {
      setTimeout(() => {
        const lastChatBox = document.getElementsByClassName(
          `chat-message-index-${index}`
        )
        if (lastChatBox && lastChatBox[0]) {
          lastChatBox[0].scrollIntoView()
        }
      }, 100)
    }
  },
  created: async function () {
    await this.getCustomers()
    await this.getLastMessages()
    this.getCustomersDebounced = _.debounce(this.getCustomers, 2000, false)
  }
})
