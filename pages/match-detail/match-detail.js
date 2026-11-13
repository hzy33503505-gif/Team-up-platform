const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    type: '',
    detail: {}
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad(options) {
    uiTheme.applyPageTheme(this)
    const type = options.type
    const id = options.id

    this.setData({
      type: type
    })

    this.getMatchDetail(type, id)
  },

  getMatchDetail(type, id) {
    wx.request({
      url: `${BASE_URL}/match/${type}/${id}`,
      method: 'GET',
      success: (res) => {
        this.setData({
          detail: res.data
        })
      },
      fail: (err) => {
        console.error('获取匹配详情失败：', err)
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    })
  },

  addToMyMatch() {
    const { type, detail } = this.data

    wx.request({
      url: `${BASE_URL}/my/matches/add`,
      method: 'POST',
      data: {
        item_id: detail.id,
        item_type: type
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
  }
})
