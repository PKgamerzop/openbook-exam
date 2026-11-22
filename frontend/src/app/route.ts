import { useSyncExternalStore } from 'react'

function subscribe(update: () => void) {
  window.addEventListener('popstate', update)
  return () => window.removeEventListener('popstate', update)
}

export function useRoute() {
  return useSyncExternalStore(subscribe, () => window.location.pathname)
}

export function navigate(path: string) {
  if (window.location.pathname === path) return
  window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo(0, 0)
}
