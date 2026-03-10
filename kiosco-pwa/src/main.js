import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ToastService from 'primevue/toastservice'
import router from './router'
import App from './App.vue'
import './style.css'
import 'primeicons/primeicons.css'

const app = createApp(App)
app.use(createPinia())
app.use(PrimeVue, {
	theme: {
		preset: Aura,
		options: {
			darkModeSelector: '.gcma-theme-dark',
		},
	},
})
app.use(ToastService)
app.use(router)
app.mount('#app')
