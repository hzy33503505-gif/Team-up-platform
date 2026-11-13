const uiTheme = require('../../utils/theme')
Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    url: ''
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad(options) {
    uiTheme.applyPageTheme(this)
    const url = decodeURIComponent(options.url || '')
    this.setData({ url })
  },

  copyLink() {
    if (!this.data.url) {
      wx.showToast({ title: '暂无链接', icon: 'none' })
      return
    }
    wx.setClipboardData({
      data: this.data.url,
      success: () => {
        wx.showToast({ title: '链接已复制', icon: 'success' })
      }
    })
  }
})
