async function userChat(path) {
    const template = await loadTemplateAsync(path)
    Vue.component('user-chat', {
        name: 'user-chat',
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
