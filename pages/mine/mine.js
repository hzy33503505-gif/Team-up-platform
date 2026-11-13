const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const REMINDER_KEY = 'contestReminders'
const REMINDER_WINDOW_DAYS = 7

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    userInfo: {
      avatarUrl: '',
      name: '',
      studentId: '',
      phone: '',
      phonePublic: false,
      qq: '',
      qqPublic: false,
      campus: '',
      college: '',
      major: '',
      grade: '',
      target: '',
      gpa: '',
      competition: '',
      project: ''
    },
    userContactText: '',
    stats: [
      { label: '已订阅竞赛', value: '0' },
      { label: '匹配记录', value: '0' },
      { label: 'AI问答', value: '18' }
    ],
    myContests: [],
    myMatches: [],
    reminderList: [],
    nextReminderText: '暂无近期报名提醒',
    reminderMap: {},
    todayReminderShown: ''
  },

  onLoad() {
    uiTheme.applyPageTheme(this)
    this.loadUserProfile()
    this.loadReminderMap()
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    this.loadUserProfile()
    this.loadReminderMap()
    this.getMyContests()
    this.getMyMatches()
  },

  loadUserProfile() {
    const profile = wx.getStorageSync('userProfile');
    if (profile) {
      this.setData({
        userInfo: {
          avatarUrl: profile.avatarUrl || '',
          name: profile.name || '',
          studentId: profile.studentId || '',
          phone: profile.phone || '',
          phonePublic: Boolean(profile.phonePublic),
          qq: profile.qq || '',
          qqPublic: Boolean(profile.qqPublic),
          campus: profile.campus || '',
          college: profile.college || '',
          major: profile.major || '',
          grade: profile.grade || '',
          target: profile.target || '',
          gpa: profile.gpa || '',
          competition: profile.competition || '',
          project: profile.project || ''
        },
        userContactText: this.buildContactText(profile)
      })
    }
  },

  buildContactText(profile) {
    const parts = []
    if (profile.studentId) parts.push(`学号：${profile.studentId}`)
    if (profile.phonePublic && profile.phone) parts.push(`手机：${profile.phone}`)
    if (profile.qqPublic && profile.qq) parts.push(`QQ：${profile.qq}`)
    return parts.join(' · ') || '未填写学号'
  },

  gotoinfor: function() {
    wx.navigateTo({
      url: '/pages/information/information'
    })
  },

  changeThemeMode(e) {
    const mode = e.currentTarget.dataset.mode
    if (!mode || mode === this.data.themeMode) return
    const nextMode = uiTheme.setThemeMode(mode)
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.themeMode = nextMode
    }
    this.setData({
      themeMode: nextMode,
      themeClass: uiTheme.getThemeClass(nextMode),
      isDarkTheme: nextMode === 'dark'
    })
    wx.showToast({
      title: nextMode === 'dark' ? '已切换深色模式' : '已切换浅色模式',
      icon: 'none'
    })
  },

  loadReminderMap() {
    const cached = wx.getStorageSync(REMINDER_KEY) || {}
    this.setData({
      reminderMap: cached
    })
  },

  saveReminderMap(nextMap) {
    wx.setStorageSync(REMINDER_KEY, nextMap)
    this.setData({
      reminderMap: nextMap
    })
  },

  getMyContests() {
    wx.request({
      url: `${BASE_URL}/my/contests`,
      method: 'GET',
      success: (res) => {
        const contests = Array.isArray(res.data) ? res.data : []
        const prepared = this.prepareContestReminders(contests)
        this.setData({
          myContests: prepared.contests,
          reminderList: prepared.reminders,
          nextReminderText: this.buildNextReminderText(prepared.reminders)
        })
        this.updateStats(prepared.contests, this.data.myMatches)
        this.showDueReminder(prepared.reminders)
      },
      fail: () => {
        wx.showToast({
          title: '我的竞赛加载失败',
          icon: 'none'
        })
      }
    })
  },

  getMyMatches() {
    if (!this.data.userInfo.studentId) {
      this.setData({ myMatches: [] })
      this.updateStats(this.data.myContests, [])
      return
    }
    wx.request({
      url: `${BASE_URL}/recruit/my`,
      method: 'POST',
      data: {
        profile: this.data.userInfo
      },
      success: (res) => {
        const payload = (res.data && res.data.data) || {}
        const matches = (payload.matched || []).map((item) => ({
          id: item.id,
          title: item.title,
          type: 'team',
          subtitle: `${item.contest_name || '队友招募'} · ${item.status || '组队中'}`,
          publisher: item.publisher_profile || {},
          publisherContactText: this.buildContactText(item.publisher_profile || {}),
          remaining: item.remaining
        }))
        this.setData({
          myMatches: matches
        })
        this.updateStats(this.data.myContests, matches)
      }
    })
  },

  updateStats(contests, matches) {
    const enabledCount = contests.filter((item) => item.reminderEnabled).length
    this.setData({
      stats: [
        { label: '已加入竞赛', value: String(contests.length) },
        { label: '报名提醒', value: String(enabledCount) },
        { label: '匹配记录', value: String(matches.length) }
      ]
    })
  },

  buildNextReminderText(reminders) {
    if (!reminders || !reminders.length) return '暂无近期报名提醒'
    const first = reminders[0]
    return `${first.name} · ${first.deadlineText}`
  },

  prepareContestReminders(contests) {
    const today = this.startOfToday()
    const reminderMap = this.data.reminderMap || {}
    const normalized = contests.map((item) => {
      const deadlineInfo = this.getDeadlineInfo(item.deadline, today)
      const reminderEnabled = Boolean(reminderMap[item.id])
      const reminderStatus = this.buildReminderStatus(deadlineInfo, reminderEnabled)
      return {
        ...item,
        ...deadlineInfo,
        reminderEnabled,
        reminderStatus
      }
    })
    const reminders = normalized
      .filter((item) => item.reminderEnabled && item.canRemind && item.daysLeft >= 0 && item.daysLeft <= REMINDER_WINDOW_DAYS)
      .sort((a, b) => a.daysLeft - b.daysLeft)
    return {
      contests: normalized,
      reminders
    }
  },

  startOfToday() {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), now.getDate())
  },

  parseDeadline(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) {
      return null
    }
    const parts = value.split('-').map(Number)
    return new Date(parts[0], parts[1] - 1, parts[2])
  },

  getDeadlineInfo(deadline, today) {
    const date = this.parseDeadline(deadline)
    if (!date) {
      return {
        canRemind: false,
        daysLeft: null,
        deadlineText: '暂无明确报名截止时间',
        deadlineLevel: 'muted'
      }
    }
    const diff = Math.ceil((date.getTime() - today.getTime()) / 86400000)
    if (diff < 0) {
      return {
        canRemind: false,
        daysLeft: diff,
        deadlineText: `已于${deadline}截止`,
        deadlineLevel: 'ended'
      }
    }
    if (diff === 0) {
      return {
        canRemind: true,
        daysLeft: diff,
        deadlineText: '今天截止',
        deadlineLevel: 'urgent'
      }
    }
    if (diff <= 3) {
      return {
        canRemind: true,
        daysLeft: diff,
        deadlineText: `${diff}天后截止`,
        deadlineLevel: 'urgent'
      }
    }
    if (diff <= REMINDER_WINDOW_DAYS) {
      return {
        canRemind: true,
        daysLeft: diff,
        deadlineText: `${diff}天后截止`,
        deadlineLevel: 'warning'
      }
    }
    return {
      canRemind: true,
      daysLeft: diff,
      deadlineText: `${diff}天后截止`,
      deadlineLevel: 'normal'
    }
  },

  buildReminderStatus(deadlineInfo, enabled) {
    if (!deadlineInfo.canRemind) {
      return deadlineInfo.daysLeft === null ? '没有明确截止时间，暂不能设置提醒' : '报名已截止'
    }
    return enabled ? `已开启提醒，${deadlineInfo.deadlineText}` : '未开启提醒'
  },

  toggleReminder(e) {
    const id = e.currentTarget.dataset.id
    const target = this.data.myContests.find((item) => item.id === id)
    if (!target) return
    if (!target.canRemind) {
      wx.showToast({
        title: target.daysLeft === null ? '暂无明确截止时间' : '报名已截止',
        icon: 'none'
      })
      return
    }
    const nextMap = {
      ...(this.data.reminderMap || {})
    }
    if (nextMap[id]) {
      delete nextMap[id]
    } else {
      nextMap[id] = {
        enabled: true,
        deadline: target.deadline,
        name: target.name,
        createdAt: this.formatDateTime(new Date())
      }
    }
    this.saveReminderMap(nextMap)
    const prepared = this.prepareContestReminders(this.data.myContests)
    this.setData({
      myContests: prepared.contests,
      reminderList: prepared.reminders
    })
    this.updateStats(prepared.contests, this.data.myMatches)
    wx.showToast({
      title: nextMap[id] ? '已开启提醒' : '已关闭提醒',
      icon: 'success'
    })
  },

  showDueReminder(reminders) {
    if (!reminders.length) return
    const todayKey = this.formatDate(new Date())
    const storageKey = `contestReminderShown:${todayKey}`
    if (wx.getStorageSync(storageKey)) return
    const first = reminders[0]
    wx.setStorageSync(storageKey, true)
    wx.showModal({
      title: '报名提醒',
      content: `${first.name}${first.deadlineText}，请尽快完成报名或材料提交。`,
      confirmText: '查看',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({
            url: `/pages/detail/detail?id=${first.id}`
          })
        }
      }
    })
  },

  goContestDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/detail/detail?id=${id}`
    })
  },

  goMyContests() {
    wx.navigateTo({
      url: '/pages/my-contests/my-contests'
    })
  },

  goMyTeams() {
    wx.navigateTo({
      url: '/pages/my-teams/my-teams'
    })
  },

  removeContest(e) {
    const id = e.currentTarget.dataset.id
    wx.request({
      url: `${BASE_URL}/my/contests/remove`,
      method: 'POST',
      data: {
        item_id: id
      },
      success: () => {
        const nextMap = {
          ...(this.data.reminderMap || {})
        }
        delete nextMap[id]
        this.saveReminderMap(nextMap)
        this.getMyContests()
      },
      fail: () => {
        wx.showToast({
          title: '删除失败',
          icon: 'none'
        })
      }
    })
  },

  removeMatch(e) {
    wx.switchTab({
      url: '/pages/match/match'
    })
  },

  formatDate(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  },

  formatDateTime(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${this.formatDate(date)} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  }
})
