const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const CHAT_KEY = 'aiAgentMessages'

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    question: '',
    loading: false,
    toView: '',
    profile: {},
    profileSummary: '',
    aiStatus: {
      label: '自训练竞赛模型',
      model: '',
      api_key_configured: false,
      modelStatusText: '自训练竞赛模型',
      modelStateText: '自训练',
      modelReady: true
    },
    quickList: [
      '根据我的资料推荐近期最适合的竞赛',
      '帮我做一个三个月竞赛生涯规划',
      '我应该怎么找队友并写申请说明',
      '帮我准备报名材料和答辩清单',
      '推荐适合AI方向的导师或课题组',
      '我的竞赛报名截止有什么风险'
    ],
    messages: []
  },

  onLoad() {
    uiTheme.applyPageTheme(this)
    this.loadProfile()
    this.loadAiStatus()
    this.loadMessages()
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    this.loadProfile()
  },

  loadAiStatus() {
    wx.request({
      url: `${BASE_URL}/ai/status`,
      method: 'GET',
      success: (res) => {
        this.setData({ aiStatus: this.decorateAiStatus(res.data || this.data.aiStatus) })
      }
    })
  },

  decorateAiStatus(status) {
    const selfModel = status.self_model || {}
    const parts = []
    if (selfModel.available) {
      parts.push(`${selfModel.label} · ${selfModel.model} · ${selfModel.docs_count}条训练文档`)
    }
    if (status.server_available) {
      parts.push(`${status.label} · ${status.model}`)
    } else if (status.provider === 'deepseek') {
      parts.push('DeepSeek V4 未配置 API Key，当前使用自训练模型')
    }
    return {
      ...status,
      modelReady: Boolean(selfModel.available),
      modelStateText: status.server_available ? '自训练优先+疑难云端' : '自训练优先',
      modelStatusText: parts.join(' / ') || '自训练竞赛模型 · 本地检索生成'
    }
  },

  loadProfile() {
    const profile = wx.getStorageSync('userProfile') || {}
    const interests = Array.isArray(profile.interests) ? profile.interests.join('、') : profile.target || ''
    const bits = [
      profile.grade,
      profile.campus,
      profile.college,
      profile.major,
      interests ? `意向：${interests}` : '',
      profile.gpa ? `学分绩：${profile.gpa}` : ''
    ].filter(Boolean)
    this.setData({
      profile,
      profileSummary: bits.join(' / ') || '未填写个人信息'
    })
  },

  loadMessages() {
    const cached = wx.getStorageSync(CHAT_KEY)
    if (Array.isArray(cached) && cached.length) {
      this.setData({ messages: cached.map((item) => this.normalizeMessage(item)) })
      return
    }
    this.setData({
      messages: [
        {
          role: '竞赛智能体',
          content: '你好，我是智竞工大竞赛智能体。我会先用本项目自训练竞赛领域模型检索和生成初稿；如果问题置信度低、需要复杂推理、规划、润色或综合分析，后端会自动调用 DeepSeek V4 做云端增强。',
          intentLabel: '初始化',
          mode: 'self_trained'
        }
      ]
    })
  },

  saveMessages(messages) {
    wx.setStorageSync(CHAT_KEY, messages.map((item) => this.normalizeMessage(item)).slice(-30))
  },

  markdownToPlainText(value) {
    return String(value || '')
      .replace(/```[\s\S]*?```/g, (match) => match.replace(/```/g, ''))
      .replace(/`([^`]+)`/g, '$1')
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1（$2）')
      .replace(/^[ \t]{0,3}#{1,6}[ \t]*/gm, '')
      .replace(/^[ \t]{0,3}>[ \t]?/gm, '')
      .replace(/^[ \t]{0,3}[-*_]{3,}[ \t]*$/gm, '')
      .replace(/(\*\*|__)(.*?)\1/g, '$2')
      .replace(/(\*|_)(.*?)\1/g, '$2')
      .replace(/^[ \t]*[-*+][ \t]+/gm, '· ')
      .replace(/^[ \t]*\|?(?:[ \t]*:?-{2,}:?[ \t]*\|)+[ \t]*$/gm, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  },

  normalizeMessage(message) {
    return {
      ...message,
      content: this.markdownToPlainText(message.content)
    }
  },

  onInput(e) {
    this.setData({
      question: e.detail.value
    })
  },

  useQuickQuestion(e) {
    const text = e.currentTarget.dataset.text
    this.setData({
      question: text
    })
  },

  useSuggestion(e) {
    const text = e.currentTarget.dataset.text
    this.setData({ question: text }, () => {
      this.sendQuestion()
    })
  },

  scrollToBottom() {
    const len = this.data.messages.length
    if (len > 0) {
      this.setData({
        toView: `msg-${len - 1}`
      })
    }
  },

  clearChat() {
    wx.removeStorageSync(CHAT_KEY)
    this.loadMessages()
    wx.showToast({ title: '已清空', icon: 'success' })
  },

  goProfile() {
    wx.navigateTo({ url: '/pages/information/information' })
  },

  sendQuestion() {
    const q = this.data.question.trim()
    if (!q || this.data.loading) return

    const userMsg = {
      role: '用户',
      content: q
    }
    const nextMessages = [...this.data.messages, userMsg]

    this.setData({
      messages: nextMessages,
      question: '',
      loading: true
    })
    this.saveMessages(nextMessages)
    this.scrollToBottom()

    wx.request({
      url: `${BASE_URL}/ask`,
      method: 'POST',
      data: {
        question: q,
        profile: this.data.profile,
        history: this.data.messages.slice(-6)
      },
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        const data = res.data || {}
        const aiMsg = {
          role: '竞赛智能体',
          content: this.markdownToPlainText(data.answer || '后端没有返回内容'),
          intent: data.intent || 'general',
          intentLabel: data.intent_label || '综合咨询',
          mode: data.mode || 'local',
          provider: data.provider || '',
          model: data.model || '',
          routeReason: data.route_reason || '',
          confidence: data.confidence || '',
          sources: data.sources || [],
          suggestions: data.suggestions || []
        }
        const messages = [...this.data.messages, aiMsg]
        this.setData({
          messages,
          loading: false
        })
        this.saveMessages(messages)
        this.scrollToBottom()
      },
      fail: (err) => {
        console.error('请求失败：', err)
        const aiMsg = {
          role: '竞赛智能体',
          content: '接口调用失败，请检查后端是否启动，以及微信开发者工具是否关闭了域名校验。',
          intentLabel: '接口错误',
          mode: 'error'
        }
        const messages = [...this.data.messages, aiMsg]
        this.setData({
          messages,
          loading: false
        })
        this.saveMessages(messages)
        this.scrollToBottom()
      }
    })
  },

  openSource(e) {
    const url = e.currentTarget.dataset.url
    const type = e.currentTarget.dataset.type
    if (url) {
      wx.navigateTo({
        url: `/pages/webview/webview?url=${encodeURIComponent(url)}`
      })
      return
    }
    if (type === 'post') {
      wx.switchTab({ url: '/pages/match/match' })
      return
    }
    wx.showToast({ title: '暂无可打开链接', icon: 'none' })
  }
})
