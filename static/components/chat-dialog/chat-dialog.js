async function chatDialog(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('chat-dialog', {
    name: 'chat-dialog',
    template,

    props: ['account', 'merchant', 'relays'],
    data: function () {
      return {
        dialog: false,
        loading: false,
        pool: null,
        nostrMessages: [],
        newMessage: ''
      }
    },
    computed: {
      sortedMessages() {
        return this.nostrMessages.sort((a, b) => b.timestamp - a.timestamp)
      }
    },
    methods: {
      async startDialog() {
        this.dialog = true
        await this.startPool()
      },
      async closeDialog() {
        this.dialog = false
        await this.pool.close(Array.from(this.relays))
      },
      async startPool() {
        this.loading = true
        this.pool = new NostrTools.SimplePool()
        let messagesMap = new Map()
        let sub = this.pool.sub(Array.from(this.relays), [
          {
            kinds: [4],
            authors: [this.account.pubkey]
          },
          {
            kinds: [4],
            '#p': [this.account.pubkey]
          }
        ])
        sub.on('eose', () => {
          this.loading = false
          this.nostrMessages = Array.from(messagesMap.values())
        })
        sub.on('event', async event => {
          let mine = event.pubkey == this.account.pubkey
          let sender = mine
            ? event.tags.find(([k, v]) => k === 'p' && v && v !== '')[1]
            : event.pubkey

          try {
            let plaintext
            if (this.account.privkey) {
              plaintext = await NostrTools.nip04.decrypt(
                this.account.privkey,
                sender,
                event.content
              )
            } else if (this.account.useExtension && this.hasNip07) {
              plaintext = await window.nostr.nip04.decrypt(
                sender,
                event.content
              )
            }
            messagesMap.set(event.id, {
              msg: plaintext,
              timestamp: timeFromNow(event.created_at * 1000),
              sender: `${mine ? 'Me' : 'Merchant'}`
            })
          } catch {
            console.error('Unable to decrypt message!')
          }
        })
        setTimeout(() => {
          this.nostrMessages = Array.from(messagesMap.values())
          this.loading = false
        }, 5000)
      },
      async sendMessage() {
        if (this.newMessage && this.newMessage.length < 1) return
        let event = {
          ...(await NostrTools.getBlankEvent()),
          kind: 4,
          created_at: Math.floor(Date.now() / 1000),
          tags: [['p', this.merchant]],
          pubkey: this.account.pubkey,
          content: await this.encryptMsg()
        }
        event.id = NostrTools.getEventHash(event)
        event.sig = this.signEvent(event)
        for (const url of Array.from(this.relays)) {
          try {
            let relay = NostrTools.relayInit(url)
            relay.on('connect', () => {
              console.debug(`connected to ${relay.url}`)
            })
            relay.on('error', () => {
              console.debug(`failed to connect to ${relay.url}`)
            })

            await relay.connect()
            let pub = relay.publish(event)
            pub.on('ok', () => {
              console.debug(`${relay.url} has accepted our event`)
            })
            pub.on('failed', reason => {
              console.debug(`failed to publish to ${relay.url}: ${reason}`)
            })
            this.newMessage = ''
          } catch (e) {
            console.error(e)
          }
        }
      },
      async encryptMsg() {
        try {
          let cypher
          if (this.account.privkey) {
            cypher = await NostrTools.nip04.encrypt(
              this.account.privkey,
              this.merchant,
              this.newMessage
            )
          } else if (this.account.useExtension && this.hasNip07) {
            cypher = await window.nostr.nip04.encrypt(
              this.merchant,
              this.newMessage
            )
          }
          return cypher
        } catch (e) {
          console.error(e)
        }
      },
      async signEvent(event) {
        if (this.account.privkey) {
          event.sig = await NostrTools.signEvent(event, this.account.privkey)
        } else if (this.account.useExtension && this.hasNip07) {
          event = await window.nostr.signEvent(event)
        }
        return event
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
