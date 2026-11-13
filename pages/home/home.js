const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')

const RECOMMENDATIONS = [
  {
    type: '专业匹配',
    title: '优先看与你专业相关的竞赛',
    desc: '先从校内认定、专业相关、准备周期合适的赛事入手，更容易形成持续积累。',
    buttonText: '查看相关竞赛',
    action: 'contest'
  },
  {
    type: '能力提升',
    title: '用 AI 助手梳理技能短板',
    desc: '可以直接询问适合的赛道、组队角色、准备节奏和材料清单，先补最短的板。',
    buttonText: '问问AI助手',
    action: 'ai'
  },
  {
    type: '低门槛尝试',
    title: '先建立参赛经验，再逐步冲高奖项',
    desc: '如果你还没有明确方向，可以先从报名条件友好、节奏清晰的比赛开始。',
    buttonText: '去竞赛中心',
    action: 'contest'
  }
]

const DEFAULT_STATS = [
  { label: '已收藏竞赛', value: 0 },
  { label: '即将截止', value: 0 },
  { label: '匹配记录', value: 0 }
]

const FALLBACK_DASHBOARD = {
  title: '智竞工大',
  subtitle: '你的竞赛成长行动台',
  recommendations: RECOMMENDATIONS,
  stats: DEFAULT_STATS,
  ai_tip: '你可以先从低门槛竞赛建立参赛经验，再逐步挑战高含金量赛事。',
  timeline: [],
  updated_at: ''
}

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    loading: false,
    title: FALLBACK_DASHBOARD.title,
    subtitle: FALLBACK_DASHBOARD.subtitle,
    recommendations: RECOMMENDATIONS,
    stats: DEFAULT_STATS,
    aiTip: FALLBACK_DASHBOARD.ai_tip,
    timeline: [],
    updatedAt: ''
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad() {
    uiTheme.applyPageTheme(this)
    this.fetchDashboard()
  },

  onPullDownRefresh() {
    this.fetchDashboard(() => wx.stopPullDownRefresh())
  },

  fetchDashboard(done) {
    this.setData({ loading: true })
    wx.request({
      url: `${BASE_URL}/home/dashboard`,
      method: 'GET',
      success: (res) => {
        this.applyDashboard(res.data || FALLBACK_DASHBOARD)
      },
      fail: () => {
        this.applyDashboard(FALLBACK_DASHBOARD)
        wx.showToast({ title: '首页加载失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ loading: false })
        if (typeof done === 'function') done()
      }
    })
  },

  normalizeStats(stats) {
    const incoming = Array.isArray(stats) ? stats : []
    const statMap = {}
    incoming.forEach((item) => {
      const label = item && item.label ? item.label : ''
      if (!label) return
      statMap[label] = Number(item.value) || 0
    })
    return DEFAULT_STATS.map((item) => ({
      label: item.label,
      value: statMap[item.label] ?? item.value
    }))
  },

  buildAiTip(text) {
    return text || FALLBACK_DASHBOARD.ai_tip
  },

  applyDashboard(payload) {
    const recommendations = (payload.recommendations || RECOMMENDATIONS).map((item) => ({
      ...item,
      buttonText: item.buttonText || item.button_text || '查看'
    }))
    const timeline = (payload.timeline || []).map((item) => ({
      ...item,
      desc: item.desc || '进入详情页查看完整信息'
    }))
    this.setData({
      title: payload.title || FALLBACK_DASHBOARD.title,
      subtitle: payload.subtitle || FALLBACK_DASHBOARD.subtitle,
      recommendations,
      stats: this.normalizeStats(payload.stats),
      aiTip: this.buildAiTip(payload.ai_tip),
      timeline,
      updatedAt: payload.updated_at || ''
    })
  },

  refreshDashboard() {
    this.fetchDashboard()
  },

  openRecommendation(e) {
    const action = e.currentTarget.dataset.action
    if (action === 'ai') {
      wx.switchTab({ url: '/pages/ai/ai' })
      return
    }
    wx.switchTab({ url: '/pages/contest/contest' })
  },

  openTimeline(e) {
    const contestId = e.currentTarget.dataset.contestid
    if (!contestId) {
      wx.switchTab({ url: '/pages/contest/contest' })
      return
    }
    wx.navigateTo({ url: `/pages/detail/detail?id=${contestId}` })
  },

  goContest() {
    wx.switchTab({ url: '/pages/contest/contest' })
  }
})
