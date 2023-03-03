async function customerStall(path) {
  const template = await loadTemplateAsync(path)
  const mock = {
    stall: '4M8j9KKGzUckHgb4C3pKCv',
    name: 'product 1',
    description:
      'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Leo integer malesuada nunc vel risus commodo. Sapien faucibus et molestie ac feugiat sed lectus vestibulum mattis. Cras ornare arcu dui vivamus. Risus pretium quam vulputate dignissim suspendisse in est ante in. Faucibus in ornare quam viverra orci sagittis eu volutpat odio.',
    amount: 100,
    price: '10',
    images: ['https://i.imgur.com/cEfpEjq.jpeg'],
    id: ['RyMbE9Hdwk9X333JKtkkNS'],
    categories: ['crafts', 'robots'],
    currency: 'EUR',
    stallName: 'stall 1',
    formatedPrice: '€10.00',
    priceInSats: 0
  }
  Vue.component('customer-stall', {
    name: 'customer-stall',
    template,

    props: ['stall', 'products', 'exchange-rates', 'product-detail'],
    data: function () {
      return {
        mock: mock
      }
    },
    methods: {},
    created() {
      console.log(this.stall)
      console.log(this.products)
    }
  })
}
