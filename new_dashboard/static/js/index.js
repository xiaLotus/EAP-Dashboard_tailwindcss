const API_BASE = "http://127.0.0.1:5000";

Vue.createApp({

    data() {
        return {
            devices: [],

            page: 0,
            perPage: 45,

            sidebarExpanded: true,

            selectedCategories: [],
            maintenanceFilter: false,
            statusFilter: 'all',

            dbList: {},

            expandedSites: {},
            expandedFloors: {},

            currentSite: '',
            currentFloor: '',
            currentLabel: '',

            username: '',
            isLogin: false,

            userState: {
                expandedSites: {},
                expandedFloors: {},
                currentSite: '',
                currentFloor: '',
                currentLabel: '',
                selectedCategories: [],   // ⭐ EAP / EQP / Switch
                maintenanceFilter: false, // ⭐ 歲修
                statusFilter: 'all',      // ⭐ alive / dead
                page: 0                   // ⭐ 第幾頁
            },

            saveTimer: null,
            searchKeyword: '',
            isSearching: false,
            isLoading: false,     // ⭐ 切換網段 loading
            loadTick: 0,          // 每次載入完成 +1，讓表格重播進場動畫
            stats: {},   // ⭐ 新增
            // ⭐ 表格內直接編輯
            editing: null,      // { ip, col }
            editValue: '',
            editSelectAll: true, // 進入編輯時是否全選（用鍵盤打字進入時不全選）
            sel: null,           // 目前選取的儲存格 { r, c }（Excel 游標）
        }
    },

    directives: {
        focus: {
            mounted(el, binding) {
                el.focus()
                if (binding.value && el.select) el.select()
                else if (el.setSelectionRange) {
                    const n = el.value.length
                    el.setSelectionRange(n, n)
                }
            }
        }
    },

    computed: {

        filteredDevices() {
            return this.devices.filter(item => {

                if (this.selectedCategories.length &&
                    !this.selectedCategories.includes(item.Category)) return false;

                if (this.maintenanceFilter && item['歲修'] !== 'Y') return false;

                if (this.statusFilter !== 'all' &&
                    item.alive_or_dead !== this.statusFilter) return false;

                if (!item.Internal_IP?.trim()) return false;

                return true;
            });
        },

        pagedColumns() {

            const items = this.filteredDevices.slice(
                this.page * this.perPage,
                (this.page + 1) * this.perPage
            );

            const colSize = 15;

            const cols = [
                items.slice(0, colSize),
                items.slice(colSize, colSize * 2),
                items.slice(colSize * 2, colSize * 3)
            ];

            cols.forEach(col => {
                while (col.length < colSize) col.push({});
            });

            return cols;
        },

        hasData() {
            return this.pagedColumns.map(col =>
                col.some(i => i.Internal_IP?.trim())
            );
        },

        // ⭐ 固定依 CSV 欄位順序顯示
        columns() {
            return [
                'Internal_IP', 'Machine_ID', 'Local', 'Device_Name',
                'TCP_Port', 'COM_Port', 'OS_Spec', 'IP_Source',
                'Category', 'Online_Test', 'Set_Time', 'Remark',
                '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead', "是否派報"
            ];
        },
        sortedDbList() {
            // 自然排序函數 (能正確處理 1F, 2F, 10F 這種字串)
            const naturalSort = (a, b) => {
                const re = /(\d+)|(\D+)/g;
                const aParts = (a || '').match(re) || [];
                const bParts = (b || '').match(re) || [];
                for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
                    const aPart = aParts[i] || '';
                    const bPart = bParts[i] || '';
                    const aNum = parseInt(aPart, 10);
                    const bNum = parseInt(bPart, 10);

                    // 如果兩段都是數字，比數字大小
                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        if (aNum !== bNum) return aNum - bNum;
                    } else {
                        // 否則比字串 (加入 'zh-TW' 讓中文排序更穩定)
                        const cmp = aPart.localeCompare(bPart, 'zh-TW');
                        if (cmp !== 0) return cmp;
                    }
                }
                return 0;
            };

            const result = {};

            // 1. 取出所有 Site 並排序 (如果 Site 也有「其他」，同樣放到最後)
            const sortedSites = Object.keys(this.dbList).sort((a, b) => {
                if (a === '其他') return 1;
                if (b === '其他') return -1;
                return naturalSort(a, b);
            });

            for (const site of sortedSites) {
                const floorsObj = this.dbList[site];

                // 2. 取出該 Site 下的所有 Floor 並排序
                const sortedFloors = Object.keys(floorsObj).sort((a, b) => {
                    // ⭐ 核心修改：如果其中一個是「其他」，強制排到最後面
                    if (a === '其他') return 1;
                    if (b === '其他') return -1;
                    // 其餘樓層使用自然排序 (1F, 2F, 10F...)
                    return naturalSort(a, b);
                });

                // 3. 按照排好的順序重新組建 Object (確保 Vue v-for 遍歷順序正確)
                const sortedFloorsObj = {};
                for (const floor of sortedFloors) {
                    sortedFloorsObj[floor] = floorsObj[floor];
                }
                result[site] = sortedFloorsObj;
            }
            return result;
        },

        totalPages() {
            return Math.max(1, Math.ceil(this.filteredDevices.length / this.perPage));
        }
    },

    methods: {

        toggleSite(site) {
            this.expandedSites[site] = !this.expandedSites[site];
            this.saveState()
        },

        toggleFloor(site, floor) {
            const key = site + '_' + floor;
            this.expandedFloors[key] = !this.expandedFloors[key];
            this.saveState()
        },

        toggleCategory(cat) {
            const i = this.selectedCategories.indexOf(cat);
            i > -1 ? this.selectedCategories.splice(i, 1) : this.selectedCategories.push(cat);
            this.page = 0;

            this.saveState()
        },

        toggleMaintenance() {
            this.maintenanceFilter = !this.maintenanceFilter;
            this.page = 0;

            this.saveState()
        },

        cycleStatus() {
            this.statusFilter =
                this.statusFilter === 'all' ? 'alive' :
                this.statusFilter === 'alive' ? 'dead' : 'all';

            this.page = 0;
            this.saveState()
        },

        nextPage() {
            this.page = (this.page + 1) % this.totalPages;
            this.saveState()
        },

        prevPage() {
            this.page = (this.page - 1 + this.totalPages) % this.totalPages;
            this.saveState()
        },

        async fetchDBList() {
            this.dbList = await (
                await fetch(`${API_BASE}/api/db_list?username=${encodeURIComponent(this.username)}`)
            ).json();
        },

        selectDB(site, floor, label) {
            // ⭐ 點擊已選取的 DB → 取消選取
            if (    this.currentSite === site &&
                    this.currentFloor === floor &&
                    this.currentLabel === label) {
                this.currentSite = ''
                this.currentFloor = ''
                this.currentLabel = ''
                this.devices = []
                this.page = 0
                this.saveState()
                return
            }

            this.currentSite = site;
            this.currentFloor = floor;
            this.currentLabel = label;
            this.page = 0;

            this.saveState()
            this.fetchData();
        },

        saveState() {
            clearTimeout(this.saveTimer)

            this.saveTimer = setTimeout(() => {

                this.userState = {
                    expandedSites: this.expandedSites,
                    expandedFloors: this.expandedFloors,
                    currentSite: this.currentSite,
                    currentFloor: this.currentFloor,
                    currentLabel: this.currentLabel,
                    selectedCategories: this.selectedCategories,
                    maintenanceFilter: this.maintenanceFilter,
                    statusFilter: this.statusFilter,
                    page: this.page
                }

                fetch(`${API_BASE}/api/save_user_state`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: this.username,
                        state: this.userState
                    })
                })

            }, 300)
        },

        async fetchData() {
            if (!this.currentSite || !this.currentLabel) return;

            this.isLoading = true
            try {
                const res = await fetch(
                    `${API_BASE}/api/devices?site=${encodeURIComponent(this.currentSite)}&floor=${encodeURIComponent(this.currentFloor)}&username=${encodeURIComponent(this.username)}&label=${encodeURIComponent(this.currentLabel)}`
                )

                const data = await res.json()

                this.devices = data.devices || []
                this.stats = data.stats || {}
                this.loadTick++
            } catch (err) {
                console.error(err);
            } finally {
                this.isLoading = false
            }
        },

        goToAuditPage() {
            // ⭐ 存登入狀態
            localStorage.setItem('isLogin', 'true')

            // ⭐ 存使用者名稱
            localStorage.setItem('username', this.username)
            window.location.href = "log.html"
        },

        // ⭐ 歲修頁面（檔名請依實際頁面調整）
        goToMaintenancePage() {
            localStorage.setItem('isLogin', 'true')
            localStorage.setItem('username', this.username)
            window.location.href = "lab.html"
        },

        async loadState() {
            try {
                const res = await fetch(`${API_BASE}/api/get_user_state?username=${this.username}`)
                const data = await res.json()

                if (!data) return

                this.expandedSites = data.expandedSites || {}
                this.expandedFloors = data.expandedFloors || {}
                this.currentSite = data.currentSite || ''
                this.currentFloor = data.currentFloor || ''
                this.currentLabel = data.currentLabel || ''

                this.selectedCategories = data.selectedCategories || []
                this.maintenanceFilter = data.maintenanceFilter || false
                this.statusFilter = data.statusFilter || 'all'
                this.page = data.page || 0

                if (this.currentSite && this.currentLabel) {
                    await this.fetchData()
                }

            } catch (e) {
                console.error('load state error', e)
            }
        },

addNetwork() {

    Swal.fire({
        html: `
            <div class="nw-head">
                <div class="nw-head-ic"><i class="fa-solid fa-network-wired"></i></div>
                <div>
                    <div class="nw-head-title">新增區網</div>
                    <div class="nw-head-sub">三種設備數量合計需為 254</div>
                </div>
            </div>
            <div class="nw-body">
                <div class="nw-row">
                    <div class="nw-field">
                        <label class="nw-label" for="swal-site">棟別 <span class="req">*</span></label>
                        <input id="swal-site" class="nw-input" placeholder="例如：K11" autocomplete="off">
                    </div>
                    <div class="nw-field">
                        <label class="nw-label" for="swal-floor">樓層 <span class="req">*</span></label>
                        <input id="swal-floor" class="nw-input" placeholder="例如：3F" autocomplete="off">
                    </div>
                </div>

                <div class="nw-field">
                    <label class="nw-label" for="swal-ip">區網網段 <span class="req">*</span></label>
                    <input id="swal-ip" class="nw-input mono" placeholder="例如：172.25.10.1" autocomplete="off">
                    <span class="nw-hint">格式為 172.x.x.1</span>
                </div>

                <div class="nw-section">
                    設備數量
                    <span id="nw-total" class="nw-total">0 / 254</span>
                </div>
                <div class="nw-row three">
                    <div class="nw-field">
                        <label class="nw-label" for="swal-eap"><span class="nw-dot eap"></span>EAP</label>
                        <input id="swal-eap" class="nw-input num" type="number" min="0" value="0">
                    </div>
                    <div class="nw-field">
                        <label class="nw-label" for="swal-eqp"><span class="nw-dot eqp"></span>EQP</label>
                        <input id="swal-eqp" class="nw-input num" type="number" min="0" value="0">
                    </div>
                    <div class="nw-field">
                        <label class="nw-label" for="swal-switch"><span class="nw-dot sw"></span>Switch</label>
                        <input id="swal-switch" class="nw-input num" type="number" min="0" value="0">
                    </div>
                </div>
            </div>
        `,
        confirmButtonText: '<i class="fa-solid fa-plus"></i>確認新增',
        cancelButtonText: '取消',
        showCancelButton: true,
        reverseButtons: true,
        buttonsStyling: false,
        focusConfirm: false,
        customClass: {
            container: 'nw-backdrop',
            popup: 'nw-popup',
            htmlContainer: 'nw-html',
            actions: 'nw-actions',
            confirmButton: 'nw-btn nw-confirm',
            cancelButton: 'nw-btn nw-cancel'
        },

        didOpen: (popup) => {
            document.getElementById('swal-site').focus()

            // ⭐ 即時顯示已分配數量
            const totalEl = document.getElementById('nw-total')
            const ids = ['swal-eap', 'swal-eqp', 'swal-switch']
            const updateTotal = () => {
                const total = ids.reduce((s, id) => s + (parseInt(document.getElementById(id).value) || 0), 0)
                totalEl.textContent = `${total} / 254`
                totalEl.className = 'nw-total' + (total === 254 ? ' ok' : total > 254 ? ' over' : '')
            }
            ids.forEach(id => {
                const el = document.getElementById(id)
                el.addEventListener('input', updateTotal)
                el.addEventListener('focus', () => el.select())
            })

            // ⭐ Enter 直接送出（中文輸入法選字時不觸發）
            popup.addEventListener('keydown', e => {
                if (e.key === 'Enter' && !e.isComposing) {
                    e.preventDefault()
                    Swal.clickConfirm()
                }
            })
        },

        preConfirm: () => {

            let site = document.getElementById('swal-site').value.trim()
            let floor = document.getElementById('swal-floor').value.trim()

            // ⭐ site：第一個字母大寫（K22）
            site = site.toUpperCase()

            // ⭐ floor：數字 + F（強制大寫）
            floor = floor.toUpperCase()

            // 補保險（避免輸入 8 / 8f）
            if (floor && !floor.endsWith('F')) {
                floor = floor.replace(/[^0-9]/g, '') + 'F'
            }
            const ip = document.getElementById('swal-ip').value.trim()

            const eapCount = parseInt(document.getElementById('swal-eap').value) || 0
            const eqpCount = parseInt(document.getElementById('swal-eqp').value) || 0
            const switchCount = parseInt(document.getElementById('swal-switch').value) || 0

            // ⭐ 基本驗證
            if (!site || !floor || floor === 'F' || !ip) {
                Swal.showValidationMessage('請填寫棟別、樓層與區網網段')
                return false
            }

            // ⭐ IP 格式驗證
            const match = ip.match(/^172\.(\d+)\.(\d+)\.1$/)
            if (!match) {
                Swal.showValidationMessage('IP 格式需為 172.x.x.1')
                return false
            }

            const subnet1 = parseInt(match[1])
            const subnet2 = parseInt(match[2])

            if (subnet1 > 255 || subnet2 > 255) {
                Swal.showValidationMessage('IP 每段數字需介於 0～255')
                return false
            }

            if ([eapCount, eqpCount, switchCount].some(n => n < 0)) {
                Swal.showValidationMessage('設備數量不可為負數')
                return false
            }

            // ⭐ 總數驗證
            const total = eapCount + eqpCount + switchCount
            const loss = 254 - total

            if (total === 0) {
                Swal.showValidationMessage('請至少輸入一個分類數量')
                return false
            }

            if (total !== 254) {
                Swal.showValidationMessage(
                    loss > 0
                        ? `總數必須為 254，目前為 ${total}，還有 ${loss} 可以用`
                        : `總數必須為 254，目前為 ${total}，超出 ${-loss}`
                )
                return false
            }

            return {
                site,
                floor,
                subnet1,
                subnet2,
                eapCount,
                eqpCount,
                switchCount
            }
        }

    }).then(result => {

        if (!result.isConfirmed) return

        const data = result.value

        // ⭐ 加 username
        data.username = this.username || localStorage.getItem('username') || ''

        console.log("送出資料:", data)

        axios.post(`${API_BASE}/api/add_network`, data, {
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(res => {

            Swal.fire({
                icon: 'success',
                title: '新增成功',
                timer: 1200,
                showConfirmButton: false
            })

            // ⭐ 可選
            this.fetchDBList()

        })
        .catch(err => {

            console.error(err)

            Swal.fire({
                icon: 'error',
                title: '新增失敗',
                text: err.response?.data?.message || err.message
            })

        })

    })
},

deleteNetwork(site, floor, label) {

    Swal.fire({
        title: '⚠️ 確認刪除',
        text: `${site}-${floor} ${label}`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: '刪除',
        cancelButtonText: '取消'
    }).then(first => {

        if (!first.isConfirmed) return

        // ⭐ 第二次確認（你要的）
        Swal.fire({
            title: '❗ 最後確認',
            text: '刪除後無法復原，確定嗎？',
            icon: 'error',
            showCancelButton: true,
            confirmButtonText: '確定刪除',
            cancelButtonText: '取消'
        }).then(second => {

            if (!second.isConfirmed) return

            axios.post(`${API_BASE}/api/delete_network`, {
                site,
                floor,
                label,
                username: this.username
            })
            .then(res => {

                Swal.fire({
                    icon: 'success',
                    title: '刪除成功',
                    timer: 1200,
                    showConfirmButton: false
                })

                // ⭐ 重新載入 DB 清單
                this.fetchDBList()

                // ⭐ 如果剛好刪掉目前 DB → 清空
                if (    this.currentSite === site &&
    this.currentFloor === floor &&
    this.currentLabel === label) {
                    this.currentSite = ''
                    this.currentFloor = ''
                    this.currentLabel = ''
                    this.devices = []
                }

            })
            .catch(err => {

                Swal.fire({
                    icon: 'error',
                    title: '刪除失敗',
                    text: err.response?.data?.message || err.message
                })

            })

        })

    })
},

async searchAllDevices() {

    if (!this.searchKeyword.trim()) {
        Swal.fire({
            icon: 'warning',
            title: '請輸入搜尋內容'
        })
        return
    }

    this.isSearching = true
    this.isLoading = true

    try {

        const res = await fetch(
            `${API_BASE}/api/search_all_devices?q=${encodeURIComponent(this.searchKeyword)}&username=${this.username}`
        )

        const data = await res.json()

        // ⭐ 直接覆蓋 devices（重點）
        this.devices = data
        this.loadTick++

        // ⭐ 重置頁數
        this.page = 0

    } catch (err) {
        console.error(err)

        Swal.fire({
            icon: 'error',
            title: '搜尋失敗'
        })
    }

    this.isSearching = false
    this.isLoading = false
},
clearSearch() {
    this.searchKeyword = ''
    this.fetchData()   // 回原本 DB
},

// ===================== Excel 式選取 / 鍵盤導覽 =====================
isSel(r, c) {
    return this.sel && this.sel.r === r && this.sel.c === c
},

selectCell(r, c) {
    this.sel = { r, c }
    this.$nextTick(() => {
        const el = document.querySelector('.sheet td.sel')
        if (el) el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    })
},

moveSel(dr, dc) {
    if (!this.sel) return
    const rows = this.filteredDevices.length
    const cols = this.columns.length
    const r = Math.min(rows - 1, Math.max(0, this.sel.r + dr))
    const c = Math.min(cols - 1, Math.max(0, this.sel.c + dc))
    this.selectCell(r, c)
},

editSelected(initial) {
    if (!this.sel) return
    const item = this.filteredDevices[this.sel.r]
    const col  = this.columns[this.sel.c]
    if (!item || this.isZeroIp(item) || !this.isEditable(col)) return
    this.editing = { ip: item.Internal_IP, col }
    if (initial !== undefined) {
        this.editValue = initial
        this.editSelectAll = false
    } else {
        this.editValue = item[col] ?? ''
        this.editSelectAll = true
    }
},

async clearSelected() {
    if (!this.sel) return
    const item = this.filteredDevices[this.sel.r]
    const col  = this.columns[this.sel.c]
    if (!item || this.isZeroIp(item) || !this.isEditable(col)) return
    if ((item[col] ?? '') === '') return
    this.editing = { ip: item.Internal_IP, col }
    this.editValue = ''
    await this.commitEdit(item, col)
},

onGridKey(e) {
    // 編輯中交給 input 自己處理
    if (this.editing) return
    if (!this.sel) return
    // ⭐ 有 SweetAlert 視窗開著時不處理表格鍵盤
    if (Swal.isVisible()) return
    const t = e.target
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return

    switch (e.key) {
        case 'ArrowUp':    e.preventDefault(); this.moveSel(-1, 0); return
        case 'ArrowDown':  e.preventDefault(); this.moveSel( 1, 0); return
        case 'ArrowLeft':  e.preventDefault(); this.moveSel(0, -1); return
        case 'ArrowRight': e.preventDefault(); this.moveSel(0,  1); return
        case 'Tab':        e.preventDefault(); this.moveSel(0, e.shiftKey ? -1 : 1); return
        case 'Home':       e.preventDefault(); this.selectCell(this.sel.r, 0); return
        case 'End':        e.preventDefault(); this.selectCell(this.sel.r, this.columns.length - 1); return
        case 'PageDown':   e.preventDefault(); this.moveSel(20, 0); return
        case 'PageUp':     e.preventDefault(); this.moveSel(-20, 0); return
        case 'Enter':
        case 'F2':         e.preventDefault(); this.editSelected(); return
        case 'Delete':
        case 'Backspace':  e.preventDefault(); this.clearSelected(); return
        case 'Escape':     this.sel = null; return
    }

    // 直接打字 → 進入編輯並以該字取代內容（Excel 行為）
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        this.editSelected(e.key)
    }
},

// 編輯框內的鍵盤：Enter 往下、Tab 往右、上下鍵也會存檔並移動
async onEditKey(e, item, col) {
    const map = {
        Enter:     [ 1, 0],
        Tab:       [ 0, e.shiftKey ? -1 : 1],
        ArrowUp:   [-1, 0],
        ArrowDown: [ 1, 0],
    }
    if (e.key === 'Escape') { e.preventDefault(); this.cancelEdit(); return }
    if (!(e.key in map)) return
    if (e.key === 'Enter' && e.shiftKey) map.Enter = [-1, 0]
    e.preventDefault()
    const [dr, dc] = map[e.key]
    await this.commitEdit(item, col)
    this.moveSel(dr, dc)
},

// ===================== 表格內直接編輯 =====================
isEditable(col) {
    return !['Internal_IP', 'File_Place'].includes(col)
},

isEditing(item, col) {
    return this.editing && this.editing.ip === item.Internal_IP && this.editing.col === col
},

selectOptions(col) {
    if (col === 'Category')      return [{v:'EAP',t:'EAP'},{v:'EQP',t:'EQP'},{v:'Switch',t:'Switch'}]
    if (col === '歲修')          return [{v:'',t:''},{v:'Y',t:'Y'},{v:'N',t:'N'}]
    if (col === 'alive_or_dead') return [{v:'alive',t:'alive'},{v:'dead',t:'dead'}]
    return null
},

startEdit(item, col) {
    if (!this.isEditable(col) || this.isZeroIp(item)) return
    if (this.isEditing(item, col)) return
    this.sel = { r: this.filteredDevices.indexOf(item), c: this.columns.indexOf(col) }
    this.editing = { ip: item.Internal_IP, col }
    this.editValue = item[col] ?? ''
    this.editSelectAll = true
},

cancelEdit() {
    this.editing = null
    this.editValue = ''
},

async commitEdit(item, col) {
    if (!this.isEditing(item, col)) return

    const newVal = String(this.editValue ?? '')
    const oldVal = String(item[col] ?? '')
    this.editing = null

    if (newVal === oldVal) return

    try {
        const payload = { ...item, [col]: newVal }

        const res = await fetch(`${API_BASE}/api/update_device`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...payload,
                site: this.currentSite || item.site,
                floor: this.currentFloor || item.floor || '',
                label: this.currentLabel || item.label,
                username: this.username
            })
        })
        const r = await res.json()

        if (r.success) {
            item[col] = newVal
            Swal.fire({ toast: true, position: 'top-end', icon: 'success',
                        title: `${item.Internal_IP}　${col} 已更新`, timer: 1200, showConfirmButton: false })
        } else {
            Swal.fire({ icon: 'error', title: '儲存失敗', text: r.error })
        }
    } catch (err) {
        console.error(err)
        Swal.fire({ icon: 'error', title: '無法連線到伺服器' })
    }
},

isZeroIp(item) {
    // 0、0.0、0.0.0、0.0.0.x 都算
    const ip = String(item.Internal_IP ?? '').trim()
    return /^0(\.0)*(\.\d+)?$/.test(ip)
},

cellClass(col, val) {
    if (col === 'Internal_IP') return 'ip'
    if (col === 'alive_or_dead') return val === 'alive' ? 'alive' : val === 'dead' ? 'dead' : ''
    if (col === '歲修' && val === 'Y') return 'maint'
    return ''
},

pct(val) {
    const v = Math.round(parseFloat(val))
    return isNaN(v) ? 0 : Math.min(100, Math.max(0, v))
},

getBarColorClass(val) {
    const v = parseFloat(val) || 0

    if (v < 50) return 'bg-red-500'
    if (v < 75) return 'bg-yellow-400'
    return 'bg-green-500'
}
    },

    mounted() {

        const username = localStorage.getItem('username');
        const isLogin = localStorage.getItem('isLogin');

        if (isLogin !== 'true' || !username) {
            location.href = "login.html";
            return;
        }

        this.username = username;
        this.isLogin = true;

        this.fetchDBList().then(() => {
            this.loadState()
        })

        window.addEventListener('keydown', e => this.onGridKey(e));
    }

}).mount('#app');