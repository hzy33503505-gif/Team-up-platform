const BASE_URL = 'http://127.0.0.1:8000'
const theme = require('./utils/theme')

App({
  onLaunch() {
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)
    theme.applyChrome()
    this.silentLogin()
  },

  silentLogin() {
    const loginToken = wx.getStorageSync('loginToken') || ''
    const openid = wx.getStorageSync('openid') || ''

    if (loginToken && openid) {
      this.globalData.loginToken = loginToken
      this.globalData.openid = openid
      return
    }

    wx.login({
      success: (res) => {
        if (!res.code) {
          console.warn('silent login skipped: missing wx.login code')
          return
        }

        wx.request({
          url: `${BASE_URL}/auth/wechat-login`,
          method: 'POST',
          data: {
            code: res.code
          },
          success: (response) => {
            const data = response.data || {}
            if (!data.ok || !data.token || !data.openid) {
              console.warn('silent login skipped: invalid backend response', data)
              return
            }
            wx.setStorageSync('loginToken', data.token)
            wx.setStorageSync('openid', data.openid)
            this.globalData.loginToken = data.token
            this.globalData.openid = data.openid
          },
          fail: (error) => {
            console.warn('silent login skipped: request failed', error)
          }
        })
      },
      fail: (error) => {
        console.warn('silent login skipped: wx.login failed', error)
      }
    })
  },

  globalData: {
    userInfo: null,
    baseUrl: BASE_URL,
    loginToken: '',
    openid: '',
    themeMode: theme.getThemeMode()
  }
})
