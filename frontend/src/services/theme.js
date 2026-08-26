import { ref } from 'vue'

const STORAGE_KEY = 'olympiads-theme'
const theme = ref('light')

function preferredTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

function applyTheme(value) {
  theme.value = value
  document.documentElement.setAttribute('data-bs-theme', value)
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', '#397698')
}

export function initializeTheme() {
  applyTheme(preferredTheme())
}

export function useTheme() {
  function toggleTheme() {
    const value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem(STORAGE_KEY, value)
    applyTheme(value)
  }
  return { theme, toggleTheme }
}
