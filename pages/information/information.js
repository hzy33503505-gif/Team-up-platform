const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const CUSTOM_CAMPUS = '其他校区（自定义）'
const CUSTOM_COLLEGE = '其他学院（自定义）'
const CUSTOM_MAJOR = '其他专业（自定义）'
const INTEREST_TAGS = ['AI', '机器人', '数学建模', '电子设计', '创新创业', '软件开发', '机械制造', '材料', '外语', '商业分析', '产品设计', '科研训练']

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
      interests: [],
      gpa: '',
      competition: '',
      project: ''
    },
    gradeOptions: ['请选择年级', '大一', '大二', '大三', '大四', '研一', '研二', '研三', '博士'],
    gradeIndex: 0,
    hitOptions: [],
    campusOptions: ['请选择校区'],
    collegeOptions: ['请选择学院'],
    majorOptions: ['请选择专业'],
    campusIndex: 0,
    collegeIndex: 0,
    majorIndex: 0,
    customCampus: '',
    customCollege: '',
    customMajor: '',
    isCustomCampus: false,
    isCustomCollege: false,
    isCustomMajor: false,
    interestOptions: [],
    customInterest: '',
    sourceText: ''
  },

  onShow() {
    uiTheme.applyPageTheme(this)
  },



  onLoad() {
    uiTheme.applyPageTheme(this)
    this.loadUserInfo()
    this.refreshInterestOptions()
    this.loadHitOptions()
  },

  loadUserInfo() {
    const cached = wx.getStorageSync('userProfile')
    if (!cached) return
    const interests = Array.isArray(cached.interests)
      ? cached.interests
      : String(cached.target || '').split(/[，,、\s]+/).filter(Boolean)
    const gradeIndex = this.data.gradeOptions.indexOf(cached.grade)
    this.setData({
      userInfo: {
        avatarUrl: cached.avatarUrl || '',
        name: cached.name || '',
        studentId: cached.studentId || '',
        phone: cached.phone || '',
        phonePublic: Boolean(cached.phonePublic),
        qq: cached.qq || '',
        qqPublic: Boolean(cached.qqPublic),
        campus: cached.campus || '',
        college: cached.college || '',
        major: cached.major || '',
        grade: cached.grade || '',
        target: cached.target || interests.join('、'),
        interests,
        gpa: cached.gpa || '',
        competition: cached.competition || '',
        project: cached.project || ''
      },
      gradeIndex: gradeIndex >= 0 ? gradeIndex : 0
    })
  },

  loadHitOptions() {
    wx.request({
      url: `${BASE_URL}/hit/options`,
      method: 'GET',
      success: (res) => {
        const data = res.data || {}
        const options = data.campuses || []
        const campusOptions = ['请选择校区', ...options.map((item) => item.name)]
        const sourceText = (data.sources || []).map((item) => item.name).join('、')
        this.setData({
          hitOptions: options,
          campusOptions,
          sourceText
        })
        this.syncIndexesFromProfile()
      },
      fail: () => {
        wx.showToast({ title: '院系数据加载失败', icon: 'none' })
      }
    })
  },

  syncIndexesFromProfile() {
    const profile = this.data.userInfo
    let campusIndex = this.data.campusOptions.indexOf(profile.campus)
    let customCampus = ''
    if (campusIndex < 0 && profile.campus) {
      campusIndex = this.data.campusOptions.indexOf(CUSTOM_CAMPUS)
      customCampus = profile.campus
    }
    campusIndex = campusIndex >= 0 ? campusIndex : 0

    const collegeOptions = this.getCollegeOptions(campusIndex)
    let collegeIndex = collegeOptions.indexOf(profile.college)
    let customCollege = ''
    if (collegeIndex < 0 && profile.college) {
      collegeIndex = collegeOptions.indexOf(CUSTOM_COLLEGE)
      customCollege = profile.college
    }
    collegeIndex = collegeIndex >= 0 ? collegeIndex : 0

    const majorOptions = this.getMajorOptions(campusIndex, collegeIndex)
    let majorIndex = majorOptions.indexOf(profile.major)
    let customMajor = ''
    if (majorIndex < 0 && profile.major) {
      majorIndex = majorOptions.indexOf(CUSTOM_MAJOR)
      customMajor = profile.major
    }

    this.setData({
      campusIndex,
      collegeOptions,
      collegeIndex,
      majorOptions,
      majorIndex: majorIndex >= 0 ? majorIndex : 0,
      customCampus,
      customCollege,
      customMajor
    })
    this.updateCustomFlags()
  },

  getCollegeOptions(campusIndex) {
    const campus = this.data.hitOptions[campusIndex - 1]
    if (!campus) return ['请选择学院']
    return ['请选择学院', ...(campus.colleges || []).map((item) => item.name)]
  },

  getMajorOptions(campusIndex, collegeIndex) {
    const campus = this.data.hitOptions[campusIndex - 1]
    const college = campus && campus.colleges ? campus.colleges[collegeIndex - 1] : null
    if (!college) return ['请选择专业']
    return ['请选择专业', ...(college.majors || [])]
  },

  updateCustomFlags() {
    this.setData({
      isCustomCampus: this.data.campusOptions[this.data.campusIndex] === CUSTOM_CAMPUS,
      isCustomCollege: this.data.collegeOptions[this.data.collegeIndex] === CUSTOM_COLLEGE,
      isCustomMajor: this.data.majorOptions[this.data.majorIndex] === CUSTOM_MAJOR
    })
  },

  onChooseAvatar(e) {
    this.setData({ 'userInfo.avatarUrl': e.detail.avatarUrl })
  },

  onCampusChange(e) {
    const campusIndex = Number(e.detail.value)
    this.setData({
      campusIndex,
      collegeIndex: 0,
      majorIndex: 0,
      collegeOptions: this.getCollegeOptions(campusIndex),
      majorOptions: ['请选择专业']
    })
    this.updateCustomFlags()
  },

  onCollegeChange(e) {
    const collegeIndex = Number(e.detail.value)
    this.setData({
      collegeIndex,
      majorIndex: 0,
      majorOptions: this.getMajorOptions(this.data.campusIndex, collegeIndex)
    })
    this.updateCustomFlags()
  },

  onMajorChange(e) {
    this.setData({ majorIndex: Number(e.detail.value) })
    this.updateCustomFlags()
  },

  onGradeChange(e) {
    const index = Number(e.detail.value)
    this.setData({
      gradeIndex: index,
      'userInfo.grade': this.data.gradeOptions[index] || ''
    })
  },

  onTextInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [field]: e.detail.value })
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`userInfo.${field}`]: e.detail.value })
  },

  onPhonePublicChange(e) {
    this.setData({ 'userInfo.phonePublic': e.detail.value })
  },

  onQqPublicChange(e) {
    this.setData({ 'userInfo.qqPublic': e.detail.value })
  },

  refreshInterestOptions() {
    const selected = this.data.userInfo.interests || []
    this.setData({
      interestOptions: INTEREST_TAGS.map((label) => ({
        label,
        selected: selected.includes(label)
      }))
    })
  },

  toggleInterest(e) {
    const label = e.currentTarget.dataset.label
    const selected = new Set(this.data.userInfo.interests || [])
    if (selected.has(label)) {
      selected.delete(label)
    } else {
      selected.add(label)
    }
    const interests = Array.from(selected)
    this.setData({
      'userInfo.interests': interests,
      'userInfo.target': interests.join('、')
    })
    this.refreshInterestOptions()
  },

  addCustomInterest() {
    const value = this.data.customInterest.trim()
    if (!value) return
    const interests = Array.from(new Set([...(this.data.userInfo.interests || []), value]))
    this.setData({
      'userInfo.interests': interests,
      'userInfo.target': interests.join('、'),
      customInterest: ''
    })
    this.refreshInterestOptions()
  },

  resolvePickerValue(options, index, customValue, customLabel, emptyLabel) {
    const value = options[index] || ''
    if (!value || value === emptyLabel) return ''
    if (value === customLabel) return customValue.trim()
    return value
  },

  onSubmit(e) {
    const formData = e.detail.value
    const campus = this.resolvePickerValue(this.data.campusOptions, this.data.campusIndex, this.data.customCampus, CUSTOM_CAMPUS, '请选择校区')
    const college = this.resolvePickerValue(this.data.collegeOptions, this.data.collegeIndex, this.data.customCollege, CUSTOM_COLLEGE, '请选择学院')
    const major = this.resolvePickerValue(this.data.majorOptions, this.data.majorIndex, this.data.customMajor, CUSTOM_MAJOR, '请选择专业')
    const grade = this.data.gradeOptions[this.data.gradeIndex] || ''
    const interests = this.data.userInfo.interests || []
    const fullData = {
      ...this.data.userInfo,
      name: formData.name,
      studentId: formData.studentId,
      phone: formData.phone,
      qq: formData.qq,
      campus,
      college,
      major,
      grade,
      target: interests.join('、'),
      gpa: formData.gpa,
      competition: formData.competition,
      project: formData.project
    }

    const required = [
      ['name', '姓名'],
      ['studentId', '学号'],
      ['campus', '校区'],
      ['college', '学院'],
      ['major', '专业'],
      ['grade', '年级']
    ]
    const missing = required
      .filter(([key]) => !fullData[key] || fullData[key].startsWith('请选择'))
      .map(([, label]) => label)

    if (missing.length) {
      wx.showToast({ title: `请补全${missing[0]}`, icon: 'none' })
      return
    }

    wx.setStorageSync('userProfile', fullData)
    wx.showToast({ title: '保存成功', icon: 'success' })
    setTimeout(() => wx.navigateBack(), 900)
  }
})
