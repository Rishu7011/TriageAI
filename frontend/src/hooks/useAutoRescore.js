/**
 * useAutoRescore.js — Polling hook that repeatedly rescores the queue.
 * Fires every `intervalMs` milliseconds (default 60000 = 1 minute).
 */
import { useEffect, useRef } from 'react'

export function useAutoRescore(onRescore, intervalMs = 60000, enabled = true) {
  const callbackRef = useRef(onRescore)
  callbackRef.current = onRescore

  useEffect(() => {
    if (!enabled) return
    const id = setInterval(() => callbackRef.current?.(), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, enabled])
}
