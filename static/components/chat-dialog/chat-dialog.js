async function chatDialog(path) {
  const template = await loadTemplateAsync(path)

  Vue.component('chat-dialog', {
    name: 'chat-dialog',
    template,

    props: ['account', 'merchant', 'relays', 'pool'],
    data: function () {
      return {
        dialog: false,
        isChat: true,
        loading: false,
        nostrMessages: [],
        newMessage: '',
        ordersTable: {
          columns: [
            {
              name: 'id',
              align: 'left',
              label: 'ID',
              field: 'id'
            },
            {
              name: 'created_at',
              align: 'left',
              label: 'Created/Updated',
              field: 'created_at',
              sortable: true
            },
            {
              name: 'paid',
              align: 'left',
              label: 'Paid',
              field: 'paid',
              sortable: true
            },
            {
              name: 'shipped',
              align: 'left',
              label: 'Shipped',
              field: 'shipped',
              sortable: true
            },
            {
              name: 'invoice',
              align: 'left',
              label: 'Invoice',
              field: row =>
                row.payment_options &&
                row.payment_options.find(p => p.type == 'ln').link
            }
          ],
          pagination: {
            rowsPerPage: 10
          }
        }
      }
    },
    computed: {
      sortedMessages() {
        return this.nostrMessages.sort((a, b) => b.created_at - a.created_at)
      },
      ordersList() {
        let orders = this.nostrMessages
          .sort((a, b) => b.created_at - a.created_at)
          .filter(o => isJson(o.msg))
          .reduce((acc, cur) => {
            const obj = JSON.parse(cur.msg)
            const key = obj.id
            const curGroup = acc[key] ?? {created_at: cur.timestamp}
            return {...acc, [key]: {...curGroup, ...obj}}
          }, {})
        return Object.values(orders)
      }
    },
    methods: {
      async startDialog() {
        this.dialog = true
        await this.startPool()
      },
      async closeDialog() {
        this.dialog = false
        await this.sub.unsub()
      },
      async startPool() {
        this.loading = true
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
          let sender = mine ? this.merchant : event.pubkey

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
            if (plaintext) {
              messagesMap.set(event.id, {
                created_at: event.created_at,
                msg: plaintext,
                timestamp: timeFromNow(event.created_at * 1000),
                sender: `${mine ? 'Me' : 'Merchant'}`
              })
              this.nostrMessages = Array.from(messagesMap.values())
            }
          } catch {
            console.error('Unable to decrypt message!')
          }
        })
        this.sub = sub
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
        // This doesn't work yet
        // this.pool.publish(Array.from(this.relays), event)
        // this.newMessage = ''
        // We need this hack
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
