const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    detail: {},
    roles: []
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad(options) {
    uiTheme.applyPageTheme(this)
    this.getTeamDetail(options.id)
  },

  getTeamDetail(id) {
    wx.request({
      url: `${BASE_URL}/recruit/post/${id}`,
      method: 'GET',
      success: (res) => {
        const detail = (res.data && res.data.data) || {}
        this.setData({
          detail,
          roles: this.prepareRoles(detail.roles || [])
        })
      },
      fail: () => {
        wx.showToast({ title: '队伍信息加载失败', icon: 'none' })
      }
    })
  },

  prepareRoles(roles) {
    return roles.map((role) => {
      const remaining = Math.max(0, Number(role.needed || 0) - Number(role.filled || 0))
      return {
        ...role,
        remaining,
        skillsText: (role.skills || []).join('、') || '未限定技能',
        statusText: remaining > 0 ? `还需${remaining}人` : '已满员'
      }
    })
  },

  goMatch() {
    wx.switchTab({ url: '/pages/match/match' })
  }
})
