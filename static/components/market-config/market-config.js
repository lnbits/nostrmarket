async function marketConfig(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('market-config', {
        name: 'market-config',
        props: ['merchants',],
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
            addMerchant: async function () {
                if (!isValidKey(this.inputPubkey, 'npub')) {
                    this.$q.notify({
                        message: 'Invalid Public Key!',
                        type: 'warning'
                    })
                    return
                }
                const publicKey = isValidKeyHex(this.inputPubkey) ? this.inputPubkey : NostrTools.nip19.decode(this.inputPubkey).data
                this.$emit('add-merchant', publicKey)
                this.inputPubkey = null
            },
            removeMerchant: async function (publicKey) {
                this.$emit('remove-merchant', publicKey)
            },
        },
        created: async function () {

        }
    })
}
