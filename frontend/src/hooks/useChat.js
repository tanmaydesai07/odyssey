import { useState, useCallback, useRef } from 'react'

export const useChat = () => {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [caseId, setCaseId] = useState(null)
  const [sessionId, setSessionId] = useState(null)

  // Use a ref to track the current assistant message being built
  // This avoids stale closure issues with async state updates
  const currentMsgRef = useRef(null)

  const createCase = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const token = localStorage.getItem('token')
      const res = await fetch('/api/cases/new', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error('Failed to create case')
      const data = await res.json()
      setCaseId(data.case._id)
      setSessionId(data.session_id)
      setMessages([])
      return data.case._id
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const loadCase = useCallback(async (id) => {
    try {
      setIsLoading(true)
      setError(null)
      const token = localStorage.getItem('token')
      const res = await fetch(`/api/cases/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to load case')
      const data = await res.json()
      setCaseId(data.case._id)
      setSessionId(data.case.sessionId)
      const chatMessages = (data.session.messages || []).map(m => ({ ...m, steps: [] }))
      setMessages(chatMessages)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(async (message) => {
    if (!caseId) throw new Error('No active case')

    try {
      setIsLoading(true)
      setError(null)

      // Add user message immediately
      setMessages(prev => [...prev, {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
        steps: [],
      }])

      const token = localStorage.getItem('token')
      const res = await fetch(`/api/cases/${caseId}/chat`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })

      if (!res.ok) throw new Error('Failed to send message')

      // Initialize the assistant message in ref AND state
      const initMsg = {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        steps: [],
      }
      currentMsgRef.current = initMsg
      setMessages(prev => [...prev, { ...initMsg }])

      // Helper: update the last message in state from the ref
      const flushToState = () => {
        setMessages(prev => {
          const n = [...prev]
          n[n.length - 1] = { ...currentMsgRef.current }
          return n
        })
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6)
          if (raw === '[DONE]') continue

          try {
            const parsed = JSON.parse(raw)

            if (parsed.type === 'answer' && parsed.content) {
              // Final answer — set content, keep all accumulated steps
              currentMsgRef.current = {
                ...currentMsgRef.current,
                content: parsed.content,
              }
              flushToState()

            } else if (parsed.type === 'plan') {
              currentMsgRef.current = {
                ...currentMsgRef.current,
                steps: [...currentMsgRef.current.steps, {
                  type: 'plan',
                  content: parsed.content,
                }],
              }
              flushToState()

            } else if (parsed.type === 'step') {
              currentMsgRef.current = {
                ...currentMsgRef.current,
                steps: [...currentMsgRef.current.steps, {
                  type: 'thought',
                  step: parsed.step,
                  content: parsed.content,
                }],
              }
              flushToState()

            } else if (parsed.type === 'tool') {
              currentMsgRef.current = {
                ...currentMsgRef.current,
                steps: [...currentMsgRef.current.steps, {
                  type: 'tool',
                  name: parsed.name,
                }],
              }
              flushToState()

            } else if (parsed.type === 'observation') {
              currentMsgRef.current = {
                ...currentMsgRef.current,
                steps: [...currentMsgRef.current.steps, {
                  type: 'observation',
                  content: parsed.content,
                }],
              }
              flushToState()

            } else if (parsed.type === 'error') {
              console.error('[useChat] Agent error:', parsed.content)
              if (!currentMsgRef.current.content) {
                currentMsgRef.current = {
                  ...currentMsgRef.current,
                  content: 'I encountered an error. Please try again.',
                }
                flushToState()
              }
            }
          } catch (e) {
            // ignore JSON parse errors
          }
        }
      }

      // Fallback if no content received
      if (!currentMsgRef.current?.content) {
        currentMsgRef.current = {
          ...currentMsgRef.current,
          content: 'I did not receive a response. Please try again.',
        }
        flushToState()
      }

      console.log('[useChat] Final message steps:', currentMsgRef.current?.steps?.length)

    } catch (err) {
      setError(err.message)
      setMessages(prev => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'assistant' && !last.content) {
          const n = [...prev]
          n[n.length - 1] = { ...last, content: 'Sorry, I encountered an error. Please try again.' }
          return n
        }
        return prev
      })
      throw err
    } finally {
      setIsLoading(false)
      currentMsgRef.current = null
    }
  }, [caseId])

  const uploadEvidence = useCallback(async (file) => {
    if (!caseId) throw new Error('No active case')
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`/api/cases/${caseId}/evidence`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    if (!res.ok) throw new Error('Upload failed')
    return await res.json()
  }, [caseId])

  const loadEvidence = useCallback(async () => {
    if (!caseId) return []
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/cases/${caseId}/evidence`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.uploads || []
  }, [caseId])

  const exportDocument = useCallback(async (draftId, format = 'pdf') => {
    if (!caseId) throw new Error('No active case')
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/cases/${caseId}/documents`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft_id: draftId, format }),
    })
    if (!res.ok) throw new Error('Export failed')
    return await res.json()
  }, [caseId])

  const downloadDocument = useCallback(async (filename) => {
    if (!caseId) throw new Error('No active case')
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/cases/${caseId}/documents/${filename}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }, [caseId])

  const downloadEvidence = useCallback(async (filename) => {
    if (!caseId) throw new Error('No active case')
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/cases/${caseId}/evidence/${filename}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }, [caseId])

  const extractFileText = useCallback(async (file) => {
    if (!caseId) throw new Error('No active case')
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`/api/cases/${caseId}/extract-text`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: 'Extraction failed' }))
      throw new Error(err.message || 'Text extraction failed')
    }
    return await res.json()
  }, [caseId])

  return { messages, isLoading, error, caseId, sessionId, createCase, loadCase, sendMessage, uploadEvidence, loadEvidence, exportDocument, downloadDocument, downloadEvidence, extractFileText }
}
