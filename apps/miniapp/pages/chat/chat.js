const API = "https://your-server.com/api"

Page({
  data: {
    messages: [],
    input: "",
    loading: false,
    scrollTo: ""
  },

  onLoad() {
    this.addMsg("agent", "Agent v5 就绪。输入任务开始。")
  },

  onInput(e) {
    this.setData({ input: e.detail.value })
  },

  addMsg(role, content) {
    const msgs = [...this.data.messages, { role, content, id: Date.now() }]
    this.setData({ messages: msgs, scrollTo: `msg-${msgs.length - 1}` })
  },

  async send() {
    const msg = this.data.input.trim()
    if (!msg || this.data.loading) return
    this.setData({ input: "", loading: true })
    this.addMsg("user", msg)

    const agentMsg = this.data.messages.length
    this.addMsg("agent", "")

    try {
      const resp = await wx.request({
        url: `${API}/chat`,
        method: "POST",
        data: { message: msg, mode: "act" },
        timeout: 120000
      })

      const data = resp.data
      const msgs = [...this.data.messages]
      msgs[agentMsg + 1] = {
        role: "agent",
        content: `${data.answer}\n\n⏱ ${data.turns} 轮 · 🔧 ${data.tool_calls} 工具调用`,
        id: Date.now()
      }
      this.setData({ messages: msgs, loading: false, scrollTo: `msg-${msgs.length - 1}` })
    } catch (e) {
      const msgs = [...this.data.messages]
      msgs[agentMsg + 1] = { role: "agent", content: `错误: ${e.errMsg}`, id: Date.now() }
      this.setData({ messages: msgs, loading: false })
    }
  }
})
