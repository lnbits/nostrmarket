async function directMessages(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('direct-messages', {
    name: 'direct-messages',
    props: ['adminkey', 'inkey'],
    template,

    data: function () {
      return {
        activePublicKey:
          '83d07a79496f4cbdc50ca585741a79a2df1fd938cfa449f0fccb0ab7352115dd',
        messages: [],
        newMessage: ''
      }
    },
    methods: {
      sendMessage: async function () {},
      getDirectMessages: async function () {
        if (!this.activePublicKey) {
          return
        }
        try {
          const {data} = await LNbits.api.request(
            'GET',
            '/nostrmarket/api/v1/message/' + this.activePublicKey,
            this.inkey
          )
          this.messages = data
          console.log(
            '### this.messages',
            this.messages.map(m => m.message)
          )
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
          console.log('###  this.messages', this.messages)
          this.newMessage = ''
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      }
    },
    created: async function () {
      await this.getDirectMessages()
    }
  })
}
