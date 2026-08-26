import { createApp } from 'vue'
import '@fortawesome/fontawesome-free/css/fontawesome.min.css'
import '@fortawesome/fontawesome-free/css/solid.min.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap'
import './styles/main.css'
import App from './App.vue'
import router from './router'
import { initializeTheme } from './services/theme'

initializeTheme()

createApp(App).use(router).mount('#app')
