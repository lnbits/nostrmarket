async function userConfig(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('user-config', {
        name: 'user-config',
        props: ['user',],
        template,

        data: function () {
            return {
            }
        },
        methods: {
            
        },
        created: async function () {

        }
    })
}
