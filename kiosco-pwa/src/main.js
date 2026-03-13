import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ToastService from 'primevue/toastservice'
import router from './router'
import App from './App.vue'
import './style.css'
import 'primeicons/primeicons.css'

const DEV_BROWSER_RESET_KEY = 'gcma-kiosco-dev-browser-reset-v1'

async function resetDevelopmentBrowserState() {
	if (!import.meta.env.DEV || typeof window === 'undefined') {
		return true
	}

	if (!['localhost', '127.0.0.1'].includes(window.location.hostname)) {
		return true
	}

	let foundPersistentState = false

	if ('serviceWorker' in navigator) {
		const registrations = await navigator.serviceWorker.getRegistrations()
		if (registrations.length > 0) {
			foundPersistentState = true
			await Promise.all(registrations.map((registration) => registration.unregister()))
		}
	}

	if ('caches' in window) {
		const cacheKeys = await caches.keys()
		const keysToDelete = cacheKeys.filter((key) =>
			key.includes('workbox') || key.includes('vite') || key.includes('kiosco')
		)

		if (keysToDelete.length > 0) {
			foundPersistentState = true
			await Promise.all(keysToDelete.map((key) => caches.delete(key)))
		}
	}

	if (foundPersistentState) {
		const alreadyReset = window.sessionStorage.getItem(DEV_BROWSER_RESET_KEY) === '1'
		if (!alreadyReset) {
			window.sessionStorage.setItem(DEV_BROWSER_RESET_KEY, '1')
			window.location.reload()
			return false
		}
	}

	window.sessionStorage.removeItem(DEV_BROWSER_RESET_KEY)
	return true
}

const canBootstrap = await resetDevelopmentBrowserState()

if (canBootstrap) {
	const pinia = createPinia()
	pinia.use(piniaPluginPersistedstate)
	
	const app = createApp(App)
	app.use(pinia)
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
}
