import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import dockerfile from 'highlight.js/lib/languages/dockerfile'
import css from 'highlight.js/lib/languages/css'
import go from 'highlight.js/lib/languages/go'
import ini from 'highlight.js/lib/languages/ini'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import makefile from 'highlight.js/lib/languages/makefile'
import markdown from 'highlight.js/lib/languages/markdown'
import nginx from 'highlight.js/lib/languages/nginx'
import python from 'highlight.js/lib/languages/python'
import shell from 'highlight.js/lib/languages/shell'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('dockerfile', dockerfile)
hljs.registerLanguage('go', go)
hljs.registerLanguage('ini', ini)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('makefile', makefile)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('nginx', nginx)
hljs.registerLanguage('python', python)
hljs.registerLanguage('shell', shell)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('yaml', yaml)

// Also register 'js' as alias for javascript
try { hljs.registerLanguage('js', javascript) } catch {}

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(code, { language: lang }).value } catch {}
    }
    return code
  },
  breaks: true,
  gfm: true,
})

export function renderMarkdown(text) {
  return marked.parse(text)
}

export function useChat() {
  const messages = ref([])
  const streaming = ref(false)
  const abortController = ref(null)

  function addMessage(text, role, image) {
    const msg = { text, role, id: Date.now() + Math.random() }
    if (image) msg.image = image
    messages.value.push(msg)
    return messages.value[messages.value.length - 1]
  }

  function clearMessages() {
    messages.value = []
  }

  function stopStream() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
  }

  function createAbortSignal() {
    abortController.value = new AbortController()
    return abortController.value.signal
  }

  async function startStream(readableStream, bubble) {
    streaming.value = true
    let reader
    try {
      reader = readableStream.getReader()
    } catch (e) {
      bubble.text = '[已取消]'
      streaming.value = false
      return
    }
    const decoder = new TextDecoder()
    let fullText = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        fullText += chunk
        bubble.text = fullText
        await nextTick()
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        bubble.text = fullText || '[已取消]'
      } else {
        bubble.text = `[网络错误: ${e.message}]`
        bubble.role = 'error'
      }
    } finally {
      streaming.value = false
      abortController.value = null
    }

    bubble.text = fullText
    return fullText
  }

  return { messages, streaming, addMessage, clearMessages, startStream, stopStream, createAbortSignal, renderMarkdown }
}
