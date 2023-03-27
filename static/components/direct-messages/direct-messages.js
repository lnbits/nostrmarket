async function directMessages(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('direct-messages', {
    name: 'direct-messages',
    props: ['adminkey', 'inkey'],
    template,

    watch: {
      activePublicKey: async function (n) {
        await this.getDirectMessages(n)
      }
    },
    data: function () {
      return {
        customers: [],
        activePublicKey: null,
        messages: [],
        newMessage: ''
      }
    },
    methods: {
      sendMessage: async function () {},
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
            '/nostrmarket/api/v1/customers',
            this.inkey
          )
          this.customers = data
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
      selectActiveCustomer: async function () {
        await this.getDirectMessages(this.activePublicKey)
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
    }
  })
}
