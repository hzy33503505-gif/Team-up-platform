const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    profile: {},
    teams: []
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    this.loadProfile()
    this.getMyTeams()
  },

  loadProfile() {
    this.setData({
      profile: wx.getStorageSync('userProfile') || {}
    })
  },

  buildContactText(profile) {
    const parts = []
    if (profile.studentId) parts.push(`学号：${profile.studentId}`)
    if (profile.phone && profile.phonePublic !== false) parts.push(`手机：${profile.phone}`)
    if (profile.qq && profile.qqPublic !== false) parts.push(`QQ：${profile.qq}`)
    return parts.join(' · ') || '暂无公开联系方式'
  },

  prepareTeam(post) {
    return {
      ...post,
      publisherContactText: this.buildContactText(post.publisher_profile || {}),
      rolesText: (post.roles || []).map((role) => {
        const remaining = Math.max(0, Number(role.needed || 0) - Number(role.filled || 0))
        return `${role.name}：${role.filled || 0}/${role.needed || 0}${remaining > 0 ? `，还需${remaining}人` : '，已满'}`
      }).join('；')
    }
  },

  getMyTeams() {
    if (!this.data.profile.studentId) {
      this.setData({ teams: [] })
      return
    }
    wx.request({
      url: `${BASE_URL}/recruit/my`,
      method: 'POST',
      data: { profile: this.data.profile },
      success: (res) => {
        const payload = (res.data && res.data.data) || {}
        this.setData({
          teams: (payload.matched || []).map((item) => this.prepareTeam(item))
        })
      },
      fail: () => {
        wx.showToast({ title: '我的组队加载失败', icon: 'none' })
      }
    })
  },

  openTeam(e) {
    wx.navigateTo({
      url: `/pages/team-detail/team-detail?id=${e.currentTarget.dataset.id}`
    })
  },

  goMatch() {
    wx.switchTab({ url: '/pages/match/match' })
  }
})
