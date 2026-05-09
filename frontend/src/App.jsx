import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = '/api' // Proxied via vite config or absolute if needed

function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState({ message: '', type: '' })
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Hello! Upload a PDF and ask me anything about it.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setUploadStatus({ message: '', type: '' })
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadStatus({ message: 'Uploading and processing...', type: 'info' })

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (res.ok) {
        setUploadStatus({ message: `Successfully processed! (${data.chunks} chunks stored)`, type: 'success' })
      } else {
        setUploadStatus({ message: data.error || 'Upload failed', type: 'error' })
      }
    } catch (err) {
      setUploadStatus({ message: 'Network error occurred', type: 'error' })
    } finally {
      setUploading(false)
    }
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMsg }),
      })
      const data = await res.json()
      
      if (res.ok) {
        setMessages(prev => [...prev, { 
          role: 'ai', 
          content: data.answer,
          sources: data.sources 
        }])
      } else {
        setMessages(prev => [...prev, { 
          role: 'ai', 
          content: `Error: ${data.error || 'Failed to get response'}` 
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: 'Sorry, a network error occurred.' 
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>SmartDesk AI</h1>
        <p>Your Intelligent Document Assistant</p>
      </header>

      <main className="grid">
        <section className="card">
          <h2>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            Ingest Document
          </h2>
          <div className="upload-section">
            <label className="file-label">
              <input type="file" className="file-input" accept=".pdf" onChange={handleFileChange} />
              <span>{file ? file.name : 'Click to select PDF'}</span>
            </label>
            <button 
              className="btn" 
              onClick={handleUpload} 
              disabled={!file || uploading}
            >
              {uploading ? 'Processing...' : 'Process PDF'}
            </button>
            {uploadStatus.message && (
              <p className={`status-msg ${uploadStatus.type}`}>
                {uploadStatus.message}
              </p>
            )}
          </div>
        </section>

        <section className="card">
          <h2>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
            Chat with Docs
          </h2>
          <div className="chat-section">
            <div className="messages">
              {messages.map((m, i) => (
                <div key={i} className={`message ${m.role}`}>
                  <div className="content">{m.content}</div>
                  {m.sources && (
                    <div className="sources">
                      {m.sources.map((s, si) => (
                        <span key={si} className="source-tag">Chunk {si+1}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {loading && <div className="message ai">Thinking...</div>}
              <div ref={messagesEndRef} />
            </div>
            <form className="message-input-container" onSubmit={handleSend}>
              <input 
                type="text" 
                placeholder="Ask a question..." 
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <button className="btn" type="submit" disabled={loading}>
                Send
              </button>
            </form>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
