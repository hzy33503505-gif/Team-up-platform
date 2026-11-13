const uiTheme = require('../../utils/theme')
// logs.js
const util = require('../../utils/util.js')

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    logs: []
  },
  onShow() {
    uiTheme.applyPageTheme(this)
  },


  onLoad() {
    uiTheme.applyPageTheme(this)
    this.setData({
      logs: (wx.getStorageSync('logs') || []).map(log => {
        return {
          date: util.formatTime(new Date(log)),
          timeStamp: log
        }
      })
    })
  }
})
