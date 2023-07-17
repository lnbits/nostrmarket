async function marketConfig(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('market-config', {
        name: 'market-config',
        props: ['merchants', 'relays', 'config'],
        template,

        data: function () {
            return {
                tab: 'merchants',
                pubkeys: new Set(),
                profiles: new Map(),
                merchantPubkey: null,
                relayUrl: null,
                configData: {
                    identifier: null,
                    name: null,
                    about: null,
                    ui: {
                        picture: null,
                        banner: null,
                        theme: null
                    }
                },
                themeOptions: [
                    'classic',
                    'bitcoin',
                    'flamingo',
                    'cyber',
                    'freedom',
                    'mint',
                    'autumn',
                    'monochrome',
                    'salvador'
                ]
            }
        },
        methods: {
            addMerchant: async function () {
                if (!isValidKey(this.merchantPubkey, 'npub')) {
                    this.$q.notify({
                        message: 'Invalid Public Key!',
                        type: 'warning'
                    })
                    return
                }
                const publicKey = isValidKeyHex(this.merchantPubkey) ? this.merchantPubkey : NostrTools.nip19.decode(this.merchantPubkey).data
                this.$emit('add-merchant', publicKey)
                this.merchantPubkey = null
            },
            removeMerchant: async function (publicKey) {
                this.$emit('remove-merchant', publicKey)
            },
            addRelay: async function () {
                const relayUrl = (this.relayUrl || '').trim()
                if (!relayUrl.startsWith('wss://') && !relayUrl.startsWith('ws://')) {
                    this.relayUrl = null
                    this.$q.notify({
                        timeout: 5000,
                        type: 'warning',
                        message: `Invalid relay URL.`,
                        caption: "Should start with 'wss://'' or 'ws://'"
                    })
                    return
                }
                try {
                    new URL(relayUrl);
                    this.$emit('add-relay', relayUrl)
                } catch (error) {
                    this.$q.notify({
                        timeout: 5000,
                        type: 'warning',
                        message: `Invalid relay URL.`,
                        caption: `Error: ${error}`
                    })
                }


                this.relayUrl = null
            },
            removeRelay: async function (relay) {
                this.$emit('remove-relay', relay)
            },
            updateUiConfig: function () {
                console.log('### this.info', this.configData)
                this.$emit('ui-config-update', this.configData)
            }
        },
        created: async function () {
            this.configData = { ...this.configData, ...this.config }
        }
    })
}
