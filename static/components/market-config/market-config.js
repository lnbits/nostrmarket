async function marketConfig(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('market-config', {
        name: 'market-config',
        props: ['adminkey',],
        template,

        data: function () {
            return {
                tab: 'merchants',
                pubkeys: new Set(),
                profiles: new Map(),
                inputPubkey: null,
            }
        },
        methods: {
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
                // this.initNostr()// todo: emit
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
                // this.initNostr() // todo: emit
            },
        },
        created: async function () {

        }
    })
}
