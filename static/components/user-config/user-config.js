async function userConfig(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('user-config', {
        name: 'user-config',
        props: ['account'],
        template,

        data: function () {
            return {
            }
        },
        methods: {
            logout: async function () {
                LNbits.utils
                    .confirmDialog(
                        'Please make sure you save your private key! You will not be able to recover it later!'
                    )
                    .onOk(async () => {
                        this.$emit('logout')
                    })
            },
            copyText(text) {
                this.$emit('copy-text', text)
            }
        },
        created: async function () {

        }
    })
}
