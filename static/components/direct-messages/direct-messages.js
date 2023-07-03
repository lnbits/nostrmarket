async function directMessages(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('direct-messages', {
    name: 'direct-messages',
    props: ['active-chat-customer', 'merchant-id', 'adminkey', 'inkey'],
    template,

    watch: {
      activeChatCustomer: async function (n) {
        this.activePublicKey = n
      },
      activePublicKey: async function (n) {
        await this.getDirectMessages(n)
      }
    },
    data: function () {
      return {
        customers: [],
        unreadMessages: 0,
        activePublicKey: null,
        messages: [],
        newMessage: '',
        showAddPublicKey: false,
        newPublicKey: null
      }
    },
    methods: {
      sendMessage: async function () {},
      buildCustomerLabel: function (c) {
        let label = `${c.profile.name || 'unknown'} ${c.profile.about || ''}`
        if (c.unread_messages) {
          label += `[new: ${c.unread_messages}]`
        }
        label += `  (${c.public_key.slice(0, 16)}...${c.public_key.slice(
          c.public_key.length - 16
        )}`
        return label
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
          this.customers = data
          this.unreadMessages = data.filter(c => c.unread_messages).length
        } catch (error) {
          LNbits.utils.notifyApiError(error)
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
      addPublicKey: async function(){
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
          this.activePublicKey = data.public_key
          await this.selectActiveCustomer()
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
          // focus back on input box
        }
        this.getCustomersDebounced()
      },
      showClientOrders: function () {
        this.$emit('customer-selected', this.activePublicKey)
      },
      selectActiveCustomer: async function () {
        await this.getDirectMessages(this.activePublicKey)
        await this.getCustomers()
      },
      focusOnChatBox: function (index) {
        setTimeout(() => {
          const lastChatBox = document.getElementsByClassName(
            `chat-mesage-index-${index}`
          )
          if (lastChatBox && lastChatBox[0]) {
            lastChatBox[0].scrollIntoView()
          }
        }, 100)
      }
    },
    created: async function () {
      await this.getCustomers()
      this.getCustomersDebounced = _.debounce(this.getCustomers, 2000, false)
    }
  })
}
