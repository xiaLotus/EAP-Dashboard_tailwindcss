// const API_BASE = "http://127.0.0.1:5000";

// Vue.createApp({

//     data() {
//         return {
//             devices: [],
//             selectedDevice: null,

//             page: 0,
//             perPage: 45,

//             sidebarExpanded: true,

//             selectedCategories: [],
//             maintenanceFilter: false,
//             statusFilter: 'all',

//             dbList: {},

//             expandedSites: {},
//             expandedFloors: {},

//             currentSite: '',
//             currentFloor: '',
//             currentLabel: '',

//             username: '',
//             isLogin: false,

//             userState: {
//                 expandedSites: {},
//                 expandedFloors: {},
//                 currentSite: '',
//                 currentFloor: '',
//                 currentLabel: '',
//                 selectedCategories: [],   // ⭐ EAP / EQP / Switch
//                 maintenanceFilter: false, // ⭐ 歲修
//                 statusFilter: 'all',      // ⭐ alive / dead
//                 page: 0                   // ⭐ 第幾頁
//             },

//             saveTimer: null,
//             searchKeyword: '',
//             isSearching: false,
//             stats: {},   // ⭐ 新增
//             statusDropdownOpen: false,
//             maintenanceDropdownOpen: false,
            
//         }
//     },

//     computed: {

//         filteredDevices() {
//             return this.devices.filter(item => {

//                 if (this.selectedCategories.length &&
//                     !this.selectedCategories.includes(item.Category)) return false;

//                 if (this.maintenanceFilter && item['歲修'] !== 'Y') return false;

//                 if (this.statusFilter !== 'all' &&
//                     item.alive_or_dead !== this.statusFilter) return false;

//                 if (!item.Internal_IP?.trim()) return false;

//                 return true;
//             });
//         },

//         pagedColumns() {

//             const items = this.filteredDevices.slice(
//                 this.page * this.perPage,
//                 (this.page + 1) * this.perPage
//             );

//             const colSize = 15;

//             const cols = [
//                 items.slice(0, colSize),
//                 items.slice(colSize, colSize * 2),
//                 items.slice(colSize * 2, colSize * 3)
//             ];

//             cols.forEach(col => {
//                 while (col.length < colSize) col.push({});
//             });

//             return cols;
//         },

//         hasData() {
//             return this.pagedColumns.map(col =>
//                 col.some(i => i.Internal_IP?.trim())
//             );
//         },

//         totalPages() {
//             return Math.max(1, Math.ceil(this.filteredDevices.length / this.perPage));
//         }
//     },

//     methods: {

//         closeDropdowns() {
//             this.statusDropdownOpen = false;
//             this.maintenanceDropdownOpen = false;
//         },

//         toggleSite(site) {
//             this.expandedSites[site] = !this.expandedSites[site];
//             this.saveState()   
//         },

//         toggleFloor(site, floor) {
//             const key = site + '_' + floor;
//             this.expandedFloors[key] = !this.expandedFloors[key];
//             this.saveState()   
//         },

//         toggleCategory(cat) {
//             const i = this.selectedCategories.indexOf(cat);
//             i > -1 ? this.selectedCategories.splice(i, 1) : this.selectedCategories.push(cat);
//             this.page = 0;

//             this.saveState()   
//         },

//         toggleMaintenance() {
//             this.maintenanceFilter = !this.maintenanceFilter;
//             this.page = 0;

//             this.saveState()   
//         },

//         cycleStatus() {
//             this.statusFilter =
//                 this.statusFilter === 'all' ? 'alive' :
//                 this.statusFilter === 'alive' ? 'dead' : 'all';

//             this.page = 0;
//             this.saveState()   
//         },

//         nextPage() {
//             this.page = (this.page + 1) % this.totalPages;
//             this.saveState()   
//         },

//         prevPage() {
//             this.page = (this.page - 1 + this.totalPages) % this.totalPages;
//             this.saveState()   
//         },

//         async fetchDBList() {
//             this.dbList = await (
//                 await fetch(`${API_BASE}/api/db_list?username=${encodeURIComponent(this.username)}`)
//             ).json();
//         },

//         selectDB(site, floor, label) {
//             // ⭐ 點擊已選取的 DB → 取消選取
//             if (    this.currentSite === site &&
//                     this.currentFloor === floor &&
//                     this.currentLabel === label) {
//                 this.currentSite = ''
//                 this.currentFloor = ''
//                 this.currentLabel = ''
//                 this.devices = []
//                 this.page = 0
//                 this.saveState()
//                 return
//             }

//             this.currentSite = site;
//             this.currentFloor = floor;
//             this.currentLabel = label;
//             this.page = 0;

//             this.saveState()
//             this.fetchData();
//         },

//         saveState() {
//             clearTimeout(this.saveTimer)

//             this.saveTimer = setTimeout(() => {

//                 this.userState = {
//                     expandedSites: this.expandedSites,
//                     expandedFloors: this.expandedFloors,
//                     currentSite: this.currentSite,
//                     currentFloor: this.currentFloor,
//                     currentLabel: this.currentLabel,
//                     selectedCategories: this.selectedCategories,
//                     maintenanceFilter: this.maintenanceFilter,
//                     statusFilter: this.statusFilter,
//                     page: this.page
//                 }

//                 fetch(`${API_BASE}/api/save_user_state`, {
//                     method: 'POST',
//                     headers: { 'Content-Type': 'application/json' },
//                     body: JSON.stringify({
//                         username: this.username,
//                         state: this.userState
//                     })
//                 })

//             }, 300)
//         },
        
//         async fetchData() {
//             if (!this.currentSite || !this.currentFloor || !this.currentLabel) return;

//             try {
//                 const res = await fetch(
//                     `${API_BASE}/api/devices?site=${this.currentSite}&floor=${this.currentFloor}&username=${this.username}&label=${encodeURIComponent(this.currentLabel)}`
//                 )

//                 const data = await res.json()

//                 this.devices = data.devices || []
//                 this.stats = data.stats || {}

//                 // console.log('📦 API 回傳完整資料:', this.devices)

//                 // console.log(`stats: ${JSON.stringify(this.stats)}`)
//             } catch (err) {
//                 console.error(err);
//             }
//         },

//         showDetail(item) {

//             const d = new Date(item.Set_Time);

//             this.selectedDevice = {
//                 ...item,
//                 Set_Time: !isNaN(d)
//                     ? `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}T00:00`
//                     : ''
//             };
//         },

//         async saveDevice(device) {

//             try {
//                 const payload = { ...device };

//                 if (payload.Set_Time) {
//                     const d = new Date(payload.Set_Time);
//                     if (!isNaN(d)) {
//                         payload.Set_Time = `${d.getFullYear()}/${d.getMonth()+1}/${d.getDate()}`;
//                     }
//                 }

//                 const res = await fetch(`${API_BASE}/api/update_device`, {
//                     method: 'POST',
//                     headers: { 'Content-Type': 'application/json' },
//                     body: JSON.stringify({
//                         ...payload,
//                         site: this.currentSite,
//                         floor: this.currentFloor,
//                         label: this.currentLabel,
//                         username: this.username
//                     })
//                 });

//                 const r = await res.json();

//                 if (r.success) {
//                     alert("✅ 更新成功");
//                     this.selectedDevice = null;
//                     this.fetchData();
//                 } else {
//                     alert("❌ 更新失敗：" + r.error);
//                 }

//             } catch (err) {
//                 console.error(err);
//                 alert("❌ API 錯誤");
//             }
//         },
//         goToAuditPage() {
//             // ⭐ 存登入狀態
//             localStorage.setItem('isLogin', 'true')

//             // ⭐ 存使用者名稱
//             localStorage.setItem('username', this.username)
//             window.location.href = "log.html"
//         },

//         async loadState() {
//             try {
//                 const res = await fetch(`${API_BASE}/api/get_user_state?username=${this.username}`)
//                 const data = await res.json()

//                 if (!data) return

//                 this.expandedSites = data.expandedSites || {}
//                 this.expandedFloors = data.expandedFloors || {}
//                 this.currentSite = data.currentSite || ''
//                 this.currentFloor = data.currentFloor || ''
//                 this.currentLabel = data.currentLabel || ''

//                 this.selectedCategories = data.selectedCategories || []
//                 this.maintenanceFilter = data.maintenanceFilter || false
//                 this.statusFilter = data.statusFilter || 'all'
//                 this.page = data.page || 0

//                 if (this.currentSite && this.currentFloor && this.currentLabel) {
//                     await this.fetchData()
//                 }

//             } catch (e) {
//                 console.error('load state error', e)
//             }
//         },

// addNetwork() {

//     Swal.fire({
//         title: '新增區網',
//         html: `
//         <div class="text-left space-y-3">

//             <div>
//                 <label class="text-xs text-gray-400">棟別</label>
//                 <input id="swal-site" class="swal2-input" placeholder="例如：K11">
//             </div>

//             <div>
//                 <label class="text-xs text-gray-400">樓層</label>
//                 <input id="swal-floor" class="swal2-input" placeholder="例如：3F">
//             </div>

//             <div>
//                 <label class="text-xs text-gray-400">區網網段</label>
//                 <input id="swal-ip" class="swal2-input" placeholder="例如：172.25.10.1">
//             </div>

//             <!-- ⭐ 三個輸入框（你要的） -->
//             <div>
//                 <label class="text-xs text-blue-400">EAP 數量</label>
//                 <input id="swal-eap" type="number" min="0" value="0" class="swal2-input">
//             </div>

//             <div>
//                 <label class="text-xs text-green-400">EQP 數量</label>
//                 <input id="swal-eqp" type="number" min="0" value="0" class="swal2-input">
//             </div>

//             <div>
//                 <label class="text-xs text-purple-400">Switch 數量</label>
//                 <input id="swal-switch" type="number" min="0" value="0" class="swal2-input">
//             </div>

//         </div>
//         `,
//         confirmButtonText: '確認',
//         cancelButtonText: '取消',
//         showCancelButton: true,
//         focusConfirm: false,

//         preConfirm: () => {

//             let site = document.getElementById('swal-site').value.trim()
//             let floor = document.getElementById('swal-floor').value.trim()

//             // ⭐ site：第一個字母大寫（K22）
//             site = site.toUpperCase()

//             // ⭐ floor：數字 + F（強制大寫）
//             floor = floor.toUpperCase()

//             // 補保險（避免輸入 8 / 8f）
//             if (!floor.endsWith('F')) {
//                 floor = floor.replace(/[^0-9]/g, '') + 'F'
//             }
//             const ip = document.getElementById('swal-ip').value.trim()

//             const eapCount = parseInt(document.getElementById('swal-eap').value) || 0
//             const eqpCount = parseInt(document.getElementById('swal-eqp').value) || 0
//             const switchCount = parseInt(document.getElementById('swal-switch').value) || 0

//             // ⭐ 基本驗證
//             if (!site || !floor || !ip) {
//                 Swal.showValidationMessage('請填寫基本資料')
//                 return false
//             }

//             // ⭐ IP 格式驗證
//             const match = ip.match(/^172\.(\d+)\.(\d+)\.1$/)
//             if (!match) {
//                 Swal.showValidationMessage('IP 格式需為 172.x.x.1')
//                 return false
//             }

//             const subnet1 = parseInt(match[1])
//             const subnet2 = parseInt(match[2])

//             // ⭐ 總數驗證
//             const total = eapCount + eqpCount + switchCount
//             const loss = 254 - total

//             if (total === 0) {
//                 Swal.showValidationMessage('請至少輸入一個分類數量')
//                 return false
//             }

//             if (total !== 254) {
//                 Swal.showValidationMessage(`總數必須為 254，目前為 ${total}，還有${loss}可以用`)
//                 return false
//             }

//             return {
//                 site,
//                 floor,
//                 subnet1,
//                 subnet2,
//                 eapCount,
//                 eqpCount,
//                 switchCount
//             }
//         }

//     }).then(result => {

//         if (!result.isConfirmed) return

//         const data = result.value

//         // ⭐ 加 username
//         data.username = this.username || localStorage.getItem('username') || ''

//         console.log("送出資料:", data)

//         axios.post(`${API_BASE}/api/add_network`, data, {
//             headers: {
//                 'Content-Type': 'application/json'
//             }
//         })
//         .then(res => {

//             Swal.fire({
//                 icon: 'success',
//                 title: '新增成功',
//                 timer: 1200,
//                 showConfirmButton: false
//             })

//             // ⭐ 可選
//             this.fetchDBList()

//         })
//         .catch(err => {

//             console.error(err)

//             Swal.fire({
//                 icon: 'error',
//                 title: '新增失敗',
//                 text: err.response?.data?.message || err.message
//             })

//         })

//     })
// },

// deleteNetwork(site, floor, label) {

//     Swal.fire({
//         title: '⚠️ 確認刪除',
//         text: `${site}-${floor} ${label}`,
//         icon: 'warning',
//         showCancelButton: true,
//         confirmButtonText: '刪除',
//         cancelButtonText: '取消'
//     }).then(first => {

//         if (!first.isConfirmed) return

//         // ⭐ 第二次確認（你要的）
//         Swal.fire({
//             title: '❗ 最後確認',
//             text: '刪除後無法復原，確定嗎？',
//             icon: 'error',
//             showCancelButton: true,
//             confirmButtonText: '確定刪除',
//             cancelButtonText: '取消'
//         }).then(second => {

//             if (!second.isConfirmed) return

//             axios.post(`${API_BASE}/api/delete_network`, {
//                 site,
//                 floor,
//                 label,
//                 username: this.username
//             })
//             .then(res => {

//                 Swal.fire({
//                     icon: 'success',
//                     title: '刪除成功',
//                     timer: 1200,
//                     showConfirmButton: false
//                 })

//                 // ⭐ 重新載入 DB 清單
//                 this.fetchDBList()

//                 // ⭐ 如果剛好刪掉目前 DB → 清空
//                 if (    this.currentSite === site &&
//     this.currentFloor === floor &&
//     this.currentLabel === label) {
//                     this.currentSite = ''
//                     this.currentFloor = ''
//                     this.devices = []
//                 }

//             })
//             .catch(err => {

//                 Swal.fire({
//                     icon: 'error',
//                     title: '刪除失敗',
//                     text: err.response?.data?.message || err.message
//                 })

//             })

//         })

//     })
// },

// async searchAllDevices() {

//     if (!this.searchKeyword.trim()) {
//         Swal.fire({
//             icon: 'warning',
//             title: '請輸入搜尋內容'
//         })
//         return
//     }

//     this.isSearching = true

//     try {

//         const res = await fetch(
//             `${API_BASE}/api/search_all_devices?q=${encodeURIComponent(this.searchKeyword)}&username=${this.username}`
//         )

//         const data = await res.json()

//         // ⭐ 直接覆蓋 devices（重點）
//         this.devices = data

//         // ⭐ 重置頁數
//         this.page = 0

//     } catch (err) {
//         console.error(err)

//         Swal.fire({
//             icon: 'error',
//             title: '搜尋失敗'
//         })
//     }

//     this.isSearching = false
// },
// clearSearch() {
//     this.searchKeyword = ''
//     this.fetchData()   // 回原本 DB
// },

// getBarColorClass(val) {
//     const v = parseFloat(val) || 0

//     if (v < 50) return 'bg-red-500'
//     if (v < 75) return 'bg-yellow-400'
//     return 'bg-green-500'
// }
//     },

//     mounted() {

//         const username = localStorage.getItem('username');
//         const isLogin = localStorage.getItem('isLogin');

//         if (isLogin !== 'true' || !username) {
//             location.href = "login.html";
//             return;
//         }

//         this.username = username;
//         this.isLogin = true;

//         this.fetchDBList().then(() => {
//             this.loadState()
//         })

//         window.addEventListener('keydown', e => {
//             if (e.key === 'ArrowRight') this.nextPage();
//             if (e.key === 'ArrowLeft') this.prevPage();
//         });
//     }

// }).mount('#app');


const API_BASE = "http://127.0.0.1:5000";

const app = Vue.createApp({

    data() {
        return {
            devices: [],
            selectedDevice: null,

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
                selectedCategories: [],
                maintenanceFilter: false,
                statusFilter: 'all',
                page: 0
            },

            saveTimer: null,
            searchKeyword: '',
            isSearching: false,
            stats: {},
            statusDropdownOpen: false,
            maintenanceDropdownOpen: false,

            // ⭐ 1. 完整定義 17 個欄位 (對應後端 CSV)
            columns: [
                "Internal_IP", "Machine_ID", "Local", "Device_Name",
                "TCP_Port", "COM_Port", "OS_Spec", "IP_Source",
                "Category", "Online_Test", "Set_Time", "Remark",
                "歲修", "File_Place", "所在區域(柱位)", "alive_or_dead", "是否派報"
            ],

            // ⭐ 2. 補齊表格編輯所需的狀態變數
            editValue: '',
            editingItem: null,
            editingCol: '',
            selectedCell: null,
            loadTick: 0
        }
    },

    computed: {
        filteredDevices() {
            return this.devices.filter(item => {
                if (this.selectedCategories.length && !this.selectedCategories.includes(item.Category)) return false;
                if (this.maintenanceFilter && item['歲修'] !== 'Y') return false;
                if (this.statusFilter !== 'all' && item.alive_or_dead !== this.statusFilter) return false;
                if (!item.Internal_IP?.trim()) return false;
                return true;
            });
        },

        pagedColumns() {
            const items = this.filteredDevices.slice(this.page * this.perPage, (this.page + 1) * this.perPage);
            const colSize = 15;
            const cols = [
                items.slice(0, colSize),
                items.slice(colSize, colSize * 2),
                items.slice(colSize * 2, colSize * 3)
            ];
            cols.forEach(col => { while (col.length < colSize) col.push({}); });
            return cols;
        },

        hasData() {
            return this.pagedColumns.map(col => col.some(i => i.Internal_IP?.trim()));
        },

        totalPages() {
            return Math.max(1, Math.ceil(this.filteredDevices.length / this.perPage));
        }
    },

    methods: {
        // ⭐ 3. 補齊 HTML 中引用的所有輔助方法
        
        // 百分比格式化
        pct(val) {
            if (val === undefined || val === null || val === '') return '0';
            const num = parseFloat(val);
            return isNaN(num) ? '0' : num.toFixed(1);
        },

        // 判斷是否為 0.0.0.x
        isZeroIp(item) {
            return item.Internal_IP && item.Internal_IP.startsWith('0.0.0.');
        },

        // 判斷儲存格是否被選取
        isSel(r, c) {
            return this.selectedCell && this.selectedCell.r === r && this.selectedCell.c === c;
        },

        // 點擊儲存格
        selectCell(r, c) {
            this.selectedCell = { r, c };
        },

        // 判斷該欄位是否可編輯
        isEditable(col) {
            const readOnly = ['Internal_IP', 'File_Place', 'alive_or_dead', '是否派報'];
            return !readOnly.includes(col);
        },

        // 判斷該欄位是否正在編輯
        isEditing(item, col) {
            return this.editingItem === item && this.editingCol === col;
        },

        // 取得下拉選單選項
        selectOptions(col) {
            if (col === 'Category') return [{ v: 'EAP', t: 'EAP' }, { v: 'EQP', t: 'EQP' }, { v: 'Switch', t: 'Switch' }, { v: '', t: '未分類' }];
            if (col === '歲修') return [{ v: 'Y', t: 'Y' }, { v: 'N', t: 'N' }, { v: '', t: '空白' }];
            return null;
        },

        // 儲存格樣式
        cellClass(col, val) {
            if (col === 'alive_or_dead') return val === 'alive' ? 'alive' : (val === 'dead' ? 'dead' : '');
            if (col === '歲修' && val === 'Y') return 'maint';
            if (col === 'Category') return val === 'EAP' ? 'cat-eap' : (val === 'EQP' ? 'cat-eqp' : (val === 'Switch' ? 'cat-switch' : ''));
            return '';
        },

        // 雙擊開始編輯
        startEdit(item, col) {
            if (!this.isEditable(col)) return;
            this.editingItem = item;
            this.editingCol = col;
            this.editValue = item[col] || '';
        },

        // 提交編輯
        async commitEdit(item, col) {
            if (!this.editingItem || this.editingCol !== col) return;

            const oldValue = String(item[col] || '');
            const newValue = String(this.editValue || '').trim();

            // 關閉編輯模式
            this.editingItem = null;
            this.editingCol = '';

            // 若無改變則不送 API
            if (oldValue === newValue) return;

            // 樂觀更新：先改前端
            item[col] = newValue;

            // 呼叫後端 API
            try {
                const payload = {
                    username: this.username,
                    site: this.currentSite,
                    floor: this.currentFloor,
                    label: this.currentLabel,
                    Internal_IP: item.Internal_IP,
                    [col]: newValue
                };

                const res = await fetch(`${API_BASE}/api/update_device`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await res.json();

                if (!result.success) {
                    Swal.fire({ icon: 'error', title: '更新失敗', text: result.error });
                    item[col] = oldValue; // 失敗則復原
                }
            } catch (err) {
                console.error('API 更新錯誤:', err);
                Swal.fire({ icon: 'error', title: '網路錯誤', text: '無法連線至伺服器' });
                item[col] = oldValue; // 失敗則復原
            }
        },

        // 編輯時的鍵盤事件
        onEditKey(event, item, col) {
            if (event.key === 'Enter') {
                event.preventDefault();
                event.target.blur();
            } else if (event.key === 'Escape') {
                this.editValue = item[col] || '';
                this.editingItem = null;
                this.editingCol = '';
            }
        },

        // === 以下為您原有的方法 ===

        closeDropdowns() {
            this.statusDropdownOpen = false;
            this.maintenanceDropdownOpen = false;
        },

        toggleSite(site) {
            this.expandedSites[site] = !this.expandedSites[site];
            this.saveState();
        },

        toggleFloor(site, floor) {
            const key = site + '_' + floor;
            this.expandedFloors[key] = !this.expandedFloors[key];
            this.saveState();
        },

        toggleCategory(cat) {
            const i = this.selectedCategories.indexOf(cat);
            i > -1 ? this.selectedCategories.splice(i, 1) : this.selectedCategories.push(cat);
            this.page = 0;
            this.saveState();
        },

        toggleMaintenance() {
            this.maintenanceFilter = !this.maintenanceFilter;
            this.page = 0;
            this.saveState();
        },

        cycleStatus() {
            this.statusFilter = this.statusFilter === 'all' ? 'alive' : this.statusFilter === 'alive' ? 'dead' : 'all';
            this.page = 0;
            this.saveState();
        },

        nextPage() {
            this.page = (this.page + 1) % this.totalPages;
            this.saveState();
        },

        prevPage() {
            this.page = (this.page - 1 + this.totalPages) % this.totalPages;
            this.saveState();
        },

        async fetchDBList() {
            this.dbList = await (await fetch(`${API_BASE}/api/db_list?username=${encodeURIComponent(this.username)}`)).json();
        },

        selectDB(site, floor, label) {
            if (this.currentSite === site && this.currentFloor === floor && this.currentLabel === label) {
                this.currentSite = ''; this.currentFloor = ''; this.currentLabel = '';
                this.devices = []; this.page = 0;
                this.saveState(); return;
            }
            this.currentSite = site; this.currentFloor = floor; this.currentLabel = label;
            this.page = 0;
            this.saveState();
            this.fetchData();
        },

        saveState() {
            clearTimeout(this.saveTimer);
            this.saveTimer = setTimeout(() => {
                this.userState = {
                    expandedSites: this.expandedSites, expandedFloors: this.expandedFloors,
                    currentSite: this.currentSite, currentFloor: this.currentFloor, currentLabel: this.currentLabel,
                    selectedCategories: this.selectedCategories, maintenanceFilter: this.maintenanceFilter,
                    statusFilter: this.statusFilter, page: this.page
                };
                fetch(`${API_BASE}/api/save_user_state`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: this.username, state: this.userState })
                });
            }, 300);
        },

        async fetchData() {
            if (!this.currentSite || !this.currentFloor || !this.currentLabel) return;
            try {
                const res = await fetch(`${API_BASE}/api/devices?site=${this.currentSite}&floor=${this.currentFloor}&username=${this.username}&label=${encodeURIComponent(this.currentLabel)}`);
                const data = await res.json();
                this.devices = data.devices || [];
                this.stats = data.stats || {};
                this.loadTick++; // 觸發表格重新渲染動畫
                                // ⭐ 新增以下除錯程式碼
                console.log("🔍 前端 columns 數量:", this.columns.length);
                if (this.devices.length > 0) {
                    console.log("🔍 第一筆資料的所有 Key:", Object.keys(this.devices[0]));
                    console.log("🔍 第一筆資料的 '是否派報' 值:", this.devices[0]['是否派報']);
                }
                // ⭐ 除錯程式碼結束
                
            } catch (err) { console.error(err); }
        },

        showDetail(item) {
            const d = new Date(item.Set_Time);
            this.selectedDevice = {
                ...item,
                Set_Time: !isNaN(d) ? `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}T00:00` : ''
            };
        },

        async saveDevice(device) {
            try {
                const payload = { ...device };
                if (payload.Set_Time) {
                    const d = new Date(payload.Set_Time);
                    if (!isNaN(d)) payload.Set_Time = `${d.getFullYear()}/${d.getMonth()+1}/${d.getDate()}`;
                }
                const res = await fetch(`${API_BASE}/api/update_device`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...payload, site: this.currentSite, floor: this.currentFloor, label: this.currentLabel, username: this.username })
                });
                const r = await res.json();
                if (r.success) { alert("✅ 更新成功"); this.selectedDevice = null; this.fetchData(); }
                else { alert("❌ 更新失敗：" + r.error); }
            } catch (err) { console.error(err); alert("❌ API 錯誤"); }
        },

        goToAuditPage() {
            localStorage.setItem('isLogin', 'true');
            localStorage.setItem('username', this.username);
            window.location.href = "log.html";
        },

        async loadState() {
            try {
                const res = await fetch(`${API_BASE}/api/get_user_state?username=${this.username}`);
                const data = await res.json();
                if (!data) return;
                this.expandedSites = data.expandedSites || {};
                this.expandedFloors = data.expandedFloors || {};
                this.currentSite = data.currentSite || '';
                this.currentFloor = data.currentFloor || '';
                this.currentLabel = data.currentLabel || '';
                this.selectedCategories = data.selectedCategories || [];
                this.maintenanceFilter = data.maintenanceFilter || false;
                this.statusFilter = data.statusFilter || 'all';
                this.page = data.page || 0;
                if (this.currentSite && this.currentFloor && this.currentLabel) await this.fetchData();
            } catch (e) { console.error('load state error', e); }
        },

        addNetwork() {
            Swal.fire({
                title: '新增區網',
                html: `
                <div class="text-left space-y-3">
                    <div><label class="text-xs text-gray-400">棟別</label><input id="swal-site" class="swal2-input" placeholder="例如：K11"></div>
                    <div><label class="text-xs text-gray-400">樓層</label><input id="swal-floor" class="swal2-input" placeholder="例如：3F"></div>
                    <div><label class="text-xs text-gray-400">區網網段</label><input id="swal-ip" class="swal2-input" placeholder="例如：172.25.10.1"></div>
                    <div><label class="text-xs text-blue-400">EAP 數量</label><input id="swal-eap" type="number" min="0" value="0" class="swal2-input"></div>
                    <div><label class="text-xs text-green-400">EQP 數量</label><input id="swal-eqp" type="number" min="0" value="0" class="swal2-input"></div>
                    <div><label class="text-xs text-purple-400">Switch 數量</label><input id="swal-switch" type="number" min="0" value="0" class="swal2-input"></div>
                </div>`,
                confirmButtonText: '確認', cancelButtonText: '取消', showCancelButton: true, focusConfirm: false,
                preConfirm: () => {
                    let site = document.getElementById('swal-site').value.trim().toUpperCase();
                    let floor = document.getElementById('swal-floor').value.trim().toUpperCase();
                    if (!floor.endsWith('F')) floor = floor.replace(/[^0-9]/g, '') + 'F';
                    const ip = document.getElementById('swal-ip').value.trim();
                    const eapCount = parseInt(document.getElementById('swal-eap').value) || 0;
                    const eqpCount = parseInt(document.getElementById('swal-eqp').value) || 0;
                    const switchCount = parseInt(document.getElementById('swal-switch').value) || 0;
                    if (!site || !floor || !ip) { Swal.showValidationMessage('請填寫基本資料'); return false; }
                    const match = ip.match(/^172\.(\d+)\.(\d+)\.1$/);
                    if (!match) { Swal.showValidationMessage('IP 格式需為 172.x.x.1'); return false; }
                    const subnet1 = parseInt(match[1]), subnet2 = parseInt(match[2]);
                    const total = eapCount + eqpCount + switchCount;
                    if (total === 0) { Swal.showValidationMessage('請至少輸入一個分類數量'); return false; }
                    if (total !== 254) { Swal.showValidationMessage(`總數必須為 254，目前為 ${total}，還有${254 - total}可以用`); return false; }
                    return { site, floor, subnet1, subnet2, eapCount, eqpCount, switchCount };
                }
            }).then(result => {
                if (!result.isConfirmed) return;
                const data = result.value;
                data.username = this.username || localStorage.getItem('username') || '';
                axios.post(`${API_BASE}/api/add_network`, data).then(res => {
                    Swal.fire({ icon: 'success', title: '新增成功', timer: 1200, showConfirmButton: false });
                    this.fetchDBList();
                }).catch(err => {
                    Swal.fire({ icon: 'error', title: '新增失敗', text: err.response?.data?.message || err.message });
                });
            });
        },

        deleteNetwork(site, floor, label) {
            Swal.fire({
                title: '⚠️ 確認刪除', text: `${site}-${floor} ${label}`, icon: 'warning',
                showCancelButton: true, confirmButtonText: '刪除', cancelButtonText: '取消'
            }).then(first => {
                if (!first.isConfirmed) return;
                Swal.fire({
                    title: '❗ 最後確認', text: '刪除後無法復原，確定嗎？', icon: 'error',
                    showCancelButton: true, confirmButtonText: '確定刪除', cancelButtonText: '取消'
                }).then(second => {
                    if (!second.isConfirmed) return;
                    axios.post(`${API_BASE}/api/delete_network`, { site, floor, label, username: this.username }).then(res => {
                        Swal.fire({ icon: 'success', title: '刪除成功', timer: 1200, showConfirmButton: false });
                        this.fetchDBList();
                        if (this.currentSite === site && this.currentFloor === floor && this.currentLabel === label) {
                            this.currentSite = ''; this.currentFloor = ''; this.devices = [];
                        }
                    }).catch(err => {
                        Swal.fire({ icon: 'error', title: '刪除失敗', text: err.response?.data?.message || err.message });
                    });
                });
            });
        },

        async searchAllDevices() {
            if (!this.searchKeyword.trim()) { Swal.fire({ icon: 'warning', title: '請輸入搜尋內容' }); return; }
            this.isSearching = true;
            try {
                const res = await fetch(`${API_BASE}/api/search_all_devices?q=${encodeURIComponent(this.searchKeyword)}&username=${this.username}`);
                const data = await res.json();
                this.devices = data;
                this.page = 0;
            } catch (err) {
                console.error(err);
                Swal.fire({ icon: 'error', title: '搜尋失敗' });
            }
            this.isSearching = false;
        },

        clearSearch() {
            this.searchKeyword = '';
            this.fetchData();
        },

        getBarColorClass(val) {
            const v = parseFloat(val) || 0;
            if (v < 50) return 'bg-red-500';
            if (v < 75) return 'bg-yellow-400';
            return 'bg-green-500';
        }
    },

    mounted() {
        const username = localStorage.getItem('username');
        const isLogin = localStorage.getItem('isLogin');
        if (isLogin !== 'true' || !username) { location.href = "login.html"; return; }
        this.username = username;
        this.isLogin = true;
        this.fetchDBList().then(() => { this.loadState(); });
        window.addEventListener('keydown', e => {
            if (e.key === 'ArrowRight') this.nextPage();
            if (e.key === 'ArrowLeft') this.prevPage();
        });
    }
});

// ⭐ 4. 註冊 v-focus 自定義指令 (讓輸入框自動聚焦並全選)
app.directive('focus', {
    mounted(el, binding) {
        setTimeout(() => {
            el.focus();
            if (binding.value) el.select();
        }, 0);
    },
    updated(el, binding) {
        if (binding.value) {
            el.focus();
            el.select();
        }
    }
});

app.mount('#app');