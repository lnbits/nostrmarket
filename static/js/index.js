const stalls = async () => {
  Vue.component(VueQrcode.name, VueQrcode)

  await relayDetails('static/components/stall-details/stall-details.html')

  new Vue({
    el: '#vue',
    mixins: [windowMixin],
    data: function () {
      return {}
    }
  })
}

stalls()
