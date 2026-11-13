const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const INTEREST_KEY = 'contestInterestStats'

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    filterList: ['全部', '校内认定', '编程', 'AI', '数学建模', '电子', '机器人', '创新创业', '机械', '材料', '外语', '设计', '交通', '海洋工程'],
    activeIndex: 0,
    keyword: '',
    contestList: [],
    recentList: [],
    hotList: [],
    contestPage: 1,
    contestPageSize: 20,
    contestTotal: 0,
    contestTotalPages: 0,
    loading: false,
    lastUpdated: '',
    profileKey: ''
  },

  onLoad() {
    uiTheme.applyPageTheme(this)
    this.getContestList(false, 1)
    this.getContestSections()
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    const profileParams = this.buildProfileParams()
    if (profileParams.profileKey !== this.data.profileKey) {
      this.getContestList(false, 1)
    }
    this.getContestSections()
  },

  onPullDownRefresh() {
    this.getContestList(true, 1).finally(() => {
      this.getContestSections()
      wx.stopPullDownRefresh()
    })
  },

  getContestList(refresh = false, page = 1) {
    const category = this.data.filterList[this.data.activeIndex]
    const contestPageSize = Math.min(50, Math.max(1, Number(this.data.contestPageSize) || 20))
    const nextPage = Math.max(1, Number(page) || 1)
    const profileParams = this.buildProfileParams()
    this.setData({ loading: true, profileKey: profileParams.profileKey })

    return new Promise((resolve) => {
      wx.request({
        url: `${BASE_URL}/contests/search`,
        method: 'GET',
        data: {
          keyword: this.data.keyword,
          category,
          refresh,
          page: nextPage,
          page_size: contestPageSize,
          campus: profileParams.campus,
          college: profileParams.college,
          major: profileParams.major,
          grade: profileParams.grade,
          target: profileParams.target,
          interests: profileParams.interests,
          competition: profileParams.competition,
          project: profileParams.project,
          gpa: profileParams.gpa
        },
        success: (res) => {
          const payload = res.data || {}
          this.setData({
            contestList: Array.isArray(payload.items) ? payload.items : [],
            contestPage: Number(payload.page) || nextPage,
            contestPageSize: Number(payload.page_size) || contestPageSize,
            contestTotal: Number(payload.total) || 0,
            contestTotalPages: Number(payload.total_pages) || 0,
            lastUpdated: this.formatTime(new Date())
          })
        },
        fail: (err) => {
          console.error('获取竞赛列表失败', err)
          wx.showToast({
            title: '竞赛数据加载失败，请确认后端已启动',
            icon: 'none'
          })
        },
        complete: () => {
          this.setData({ loading: false })
          resolve()
        }
      })
    })
  },

  buildProfileParams() {
    const profile = wx.getStorageSync('userProfile') || {}
    const interests = Array.isArray(profile.interests)
      ? profile.interests.join('、')
      : String(profile.interests || profile.target || '')
    const params = {
      campus: profile.campus || '',
      college: profile.college || '',
      major: profile.major || '',
      grade: profile.grade || '',
      target: profile.target || '',
      interests,
      competition: profile.competition || '',
      project: profile.project || '',
      gpa: profile.gpa || ''
    }
    return {
      ...params,
      profileKey: JSON.stringify(params)
    }
  },

  getContestSections() {
    wx.request({
      url: `${BASE_URL}/contests/sections`,
      method: 'GET',
      success: (res) => {
        const data = res.data || {}
        const decorateHot = (item) => ({
          ...item,
          hotText: item.global_click_count
            ? `全站${item.global_click_count}次 · ${item.global_click_rate || 0}%`
            : '暂无全站点击'
        })
        this.setData({
          recentList: Array.isArray(data.recent) ? data.recent : [],
          hotList: Array.isArray(data.hot) ? data.hot.map(decorateHot) : []
        })
      }
    })
  },

  formatTime(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`
  },

  onSearchInput(e) {
    this.setData({
      keyword: e.detail.value
    })
  },

  searchContest() {
    this.getContestList(false, 1)
  },

  changeFilter(e) {
    const index = e.currentTarget.dataset.index
    this.setData({
      activeIndex: index
    })
    this.getContestList(false, 1)
  },

  refreshData() {
    this.getContestList(true, 1).then(() => {
      this.getContestSections()
    })
  },

  prevContestPage() {
    if (this.data.contestPage <= 1) return
    this.getContestList(false, this.data.contestPage - 1)
  },

  nextContestPage() {
    if (this.data.contestPage >= this.data.contestTotalPages) return
    this.getContestList(false, this.data.contestPage + 1)
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id
    this.rememberContestInterest(id)
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  },

  openOfficial(e) {
    const link = e.currentTarget.dataset.notice || e.currentTarget.dataset.link
    const id = e.currentTarget.dataset.id
    if (!link) {
      wx.showToast({ title: '暂无官网链接', icon: 'none' })
      return
    }
    this.recordHit(id)
    this.rememberContestInterest(id)
    wx.navigateTo({
      url: `/pages/webview/webview?url=${encodeURIComponent(link)}`
    })
  },

  recordHit(id) {
    if (!id) return
    wx.request({
      url: `${BASE_URL}/contests/hit`,
      method: 'POST',
      data: {
        item_id: id
      },
      complete: () => {
        this.getContestSections()
      }
    })
  },

  rememberContestInterest(id) {
    const source = [
      ...this.data.contestList,
      ...this.data.recentList,
      ...this.data.hotList
    ]
    const item = source.find((row) => row.id === id)
    if (!item) return
    const stats = wx.getStorageSync(INTEREST_KEY) || { tags: {}, contests: {} }
    const tags = [item.category, ...(item.keywords || [])].filter(Boolean).slice(0, 6)
    tags.forEach((tag) => {
      stats.tags[tag] = (stats.tags[tag] || 0) + 1
    })
    stats.contests[id] = {
      name: item.name,
      category: item.category,
      updatedAt: Date.now()
    }
    wx.setStorageSync(INTEREST_KEY, stats)
  }
})
