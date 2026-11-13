const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const INTEREST_KEY = 'contestInterestStats'

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    detail: {},
    relatedTeams: []
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad(options) {
    uiTheme.applyPageTheme(this)
    this.getDetail(options.id)
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage']
    })
  },

  getDetail(id) {
    wx.request({
      url: `${BASE_URL}/contest/${id}`,
      method: 'GET',
      success: (res) => {
        this.setData({
          detail: res.data || {}
        })
        this.recordHit(res.data && res.data.id)
        this.rememberContestInterest(res.data || {})
        this.loadRelatedTeams(res.data || {})
      },
      fail: (err) => {
        console.error('获取详情失败：', err)
        wx.showToast({
          title: '加载失败，请确认后端已启动',
          icon: 'none'
        })
      }
    })
  },

  loadRelatedTeams(detail) {
    const contestName = String(detail.name || '').trim()
    if (!contestName) return
    wx.request({
      url: `${BASE_URL}/recruit/posts`,
      method: 'GET',
      success: (res) => {
        const posts = Array.isArray(res.data) ? res.data : []
        const relatedTeams = posts
          .filter((post) => this.isRelatedTeam(post, contestName))
          .slice(0, 5)
          .map((post) => this.prepareTeam(post))
        this.setData({ relatedTeams })
      }
    })
  },

  isRelatedTeam(post, contestName) {
    const target = String(post.contest_name || '').trim()
    if (!target) return false
    return target === contestName || target.includes(contestName) || contestName.includes(target)
  },

  prepareTeam(post) {
    const roles = post.roles || []
    const remaining = roles.reduce((sum, role) => {
      return sum + Math.max(0, Number(role.needed || 0) - Number(role.filled || 0))
    }, 0)
    return {
      id: post.id,
      title: post.title,
      contest_name: post.contest_name,
      status: remaining > 0 ? `还需${remaining}人` : '已满员',
      publisher: (post.publisher_profile || {}).name || '匿名发布者',
      rolesText: roles.map((role) => role.name).filter(Boolean).join('、') || '综合协作'
    }
  },

  openOfficial() {
    const link = this.data.detail.latest_notice_link || this.data.detail.official_link
    if (!link) {
      wx.showToast({ title: '暂无官网链接', icon: 'none' })
      return
    }
    this.recordHit(this.data.detail.id)
    wx.navigateTo({
      url: `/pages/webview/webview?url=${encodeURIComponent(link)}`
    })
  },

  copyOfficialLink() {
    const link = this.data.detail.latest_notice_link || this.data.detail.official_link
    if (!link) {
      wx.showToast({ title: '暂无官网链接', icon: 'none' })
      return
    }
    wx.setClipboardData({
      data: link,
      success: () => {
        wx.showToast({ title: '官网链接已复制', icon: 'success' })
      }
    })
  },

  addToMyContest() {
    const id = this.data.detail.id
    wx.request({
      url: `${BASE_URL}/my/contests/add`,
      method: 'POST',
      data: {
        item_id: id
      },
      success: (res) => {
        wx.showToast({
          title: res.data.message || '已加入',
          icon: res.data.ok === false ? 'none' : 'success'
        })
      },
      fail: () => {
        wx.showToast({
          title: '操作失败',
          icon: 'none'
        })
      }
    })
  },

  openTeamDetail(e) {
    wx.navigateTo({
      url: `/pages/team-detail/team-detail?id=${e.currentTarget.dataset.id}`
    })
  },

  onShareAppMessage() {
    const detail = this.data.detail || {}
    return {
      title: detail.name ? `推荐竞赛：${detail.name}` : '智竞工大竞赛详情',
      path: `/pages/detail/detail?id=${detail.id || ''}`
    }
  },

  recordHit(id) {
    if (!id) return
    wx.request({
      url: `${BASE_URL}/contests/hit`,
      method: 'POST',
      data: {
        item_id: id
      }
    })
  },

  rememberContestInterest(item) {
    if (!item || !item.id) return
    const stats = wx.getStorageSync(INTEREST_KEY) || { tags: {}, contests: {} }
    const tags = [item.category, ...(item.keywords || [])].filter(Boolean).slice(0, 6)
    tags.forEach((tag) => {
      stats.tags[tag] = (stats.tags[tag] || 0) + 1
    })
    stats.contests[item.id] = {
      name: item.name,
      category: item.category,
      updatedAt: Date.now()
    }
    wx.setStorageSync(INTEREST_KEY, stats)
  }
})
