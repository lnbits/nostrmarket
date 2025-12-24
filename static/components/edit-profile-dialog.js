window.app.component('edit-profile-dialog', {
  name: 'edit-profile-dialog',
  template: '#edit-profile-dialog',
  delimiters: ['${', '}'],
  props: ['model-value', 'merchant-id', 'merchant-config', 'adminkey'],
  emits: ['update:model-value', 'profile-updated'],
  data: function () {
    return {
      saving: false,
      formData: {
        name: '',
        display_name: '',
        about: '',
        picture: '',
        banner: '',
        website: '',
        nip05: '',
        lud16: ''
      }
    }
  },
  computed: {
    show: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:model-value', value)
      }
    }
  },
  methods: {
    saveProfile: async function () {
      this.saving = true
      try {
        const config = {
          ...this.merchantConfig,
          name: this.formData.name || null,
          display_name: this.formData.display_name || null,
          about: this.formData.about || null,
          picture: this.formData.picture || null,
          banner: this.formData.banner || null,
          website: this.formData.website || null,
          nip05: this.formData.nip05 || null,
          lud16: this.formData.lud16 || null
        }
        await LNbits.api.request(
          'PATCH',
          `/nostrmarket/api/v1/merchant/${this.merchantId}`,
          this.adminkey,
          config
        )
        // Publish to Nostr
        await LNbits.api.request(
          'PUT',
          `/nostrmarket/api/v1/merchant/${this.merchantId}/nostr`,
          this.adminkey
        )
        this.show = false
        this.$q.notify({
          type: 'positive',
          message: 'Profile saved and published to Nostr!'
        })
        this.$emit('profile-updated')
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.saving = false
      }
    },
    loadFormData: function () {
      if (this.merchantConfig) {
        this.formData.name = this.merchantConfig.name || ''
        this.formData.display_name = this.merchantConfig.display_name || ''
        this.formData.about = this.merchantConfig.about || ''
        this.formData.picture = this.merchantConfig.picture || ''
        this.formData.banner = this.merchantConfig.banner || ''
        this.formData.website = this.merchantConfig.website || ''
        this.formData.nip05 = this.merchantConfig.nip05 || ''
        this.formData.lud16 = this.merchantConfig.lud16 || ''
      }
    }
  },
  watch: {
    modelValue(newVal) {
      if (newVal) {
        this.loadFormData()
      }
    }
  }
})
