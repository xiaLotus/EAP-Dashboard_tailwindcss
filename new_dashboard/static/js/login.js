const { createApp } = Vue

const API = "http://127.0.0.1:5000"

createApp({
    data() {
        return {
            username: '',
            password: '',
            errorMsg: '',
            loading: false,
            showPw: false
        }
    },
    methods: {

        clearInput() {
            this.username = ''
            this.password = ''
            this.errorMsg = ''
        },

        async login() {
            this.errorMsg = ''

            if (!this.username || !this.password) {
                this.errorMsg = '請輸入帳號與密碼'
                return
            }

            if (this.loading) return
            this.loading = true

            try {
                const res = await fetch(`${API}/api/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: this.username.trim(),
                        password: this.password
                    })
                })

                const data = await res.json().catch(() => ({}))

                if (res.ok && data.success) {
                    // ⭐ 存登入狀態
                    localStorage.setItem('isLogin', 'true')
                    localStorage.setItem('username', data.username || this.username.trim())
                    localStorage.setItem('loginTime', new Date().toISOString())

                    // ⭐ 跳轉
                    window.location.href = "index.html"
                } else {
                    this.errorMsg = data.message || '帳號或密碼錯誤'
                }
            } catch (err) {
                console.error('login error:', err)
                this.errorMsg = '無法連線到伺服器'
            } finally {
                this.loading = false
            }
        }
    }
}).mount('#app')