
const app = Vue.createApp({    
    data(){
        return{
            username: '',
            // 現在時間
            currentYear: new Date().getFullYear(),
            // 存放 unitfolders 名稱，用於 sidebar 顯示
            unitfolders: [],
            // 存放各棟各樓層 資料，用於下拉式選單
            floorfolders: [],
            // 計算重複點擊 unit 時，floorfloders 縮回
            press_unit: false,

            // 針對棟別
            // 選擇的棟別名稱 (暫存，負責轉移用的，會變null)
            selectedUnit: '',  
            // 儲存選擇的棟別資料夾名稱 (也是暫存，但這要在更換 FolderName 時才會更換)
            selectedUnitName: '', 

            // 針對樓層
            // 選擇的棟別名稱 (暫存，負責轉移用的，會變null)
            selectedFloor: '',  
            // 儲存選擇的樓層資料夾名稱 (也是暫存，但這要在更換 FolderName 時才會更換)
            selectedFloorName: '', 

            // 針對選擇的樓層 + 區網檔案名稱
            // 選擇的樓層 + 區網檔案名稱 (暫存，負責轉移用的，會變null)
            selectedFileFolder: '',
            // 儲存選擇的檔案名稱 (也是暫存，但這要在更換 FolderName 時才會更換)
            selectedFileFolderName: '',

            // 存放檔案名稱的 folders
            files: [],

            isSubSidebarVisible: false,

            // EAP IP的表
            showEAP_IPcard: false,

            // ----------------
            // 底下循環卡片
            // 所有卡片數據
            cardData: [], 
            // 當前卡片
            currentCard: null, 
            // 當前頁
            currentPage: 1, 
            // 當前編輯的項目
            currentItem: null,
            // 每頁顯示條數
            pageSize: 45,
            // --------------

            // 每層
            eachfloor: {},
            // 每層輪換4個
            numColumns: 4,

            // 是否進入編輯各 IP 狀態
            isEditing: false,

            // 針對每個需要更新或是新增的區塊做update
            currentItem: {
                ip: '',
                machine_id: '',
                local: '',
                Column_Position: '',
                device_name: '',
                tcp_port: '',
                com_port: '',
                os_spec: '',
                ip_source: '',
                new_rule: '',
                online_test: '',
                set_time: '',
                remark: '',
                suixiu: ''
            },

            // 呈現每層有多少%
            showEachFloor: false,
            // 呈現可以上傳或是下載的區塊
            showmovein_detail: false,

            // 下載的card
            showdownloadcard: false,

            // -------------------------
            // progress bar
            progressBar1: 0, // 全部
            progressBar2: 0, // EAP
            progressBar3: 0, // EQP 
            progressBar4: 0, // Switch 
            targetProgress1: 0, // 設定第一個進度條的目標值 // 全部
            targetProgress2: 0, // 設定第二個進度條的目標值 // EAP
            targetProgress3: 0, // 設定第一個進度條的目標值 // EQP
            targetProgress4: 0, // Switch 

            // ip妥善率，EAP妥善率 分母分子 (對包含歲修的各表)
            ip_Success_Rate: '',
            EAP_Success_Rate: '',
            EQP_Success_Rate: '',
            Switch_Success_Rate: '',
            
            // 針對歲修
            F1_EAP_Success_Rate: '',
            F3_EAP_Success_Rate: '',
            F5_EAP_Success_Rate: '',

            // 針對F1 + F3 的大半圓餅
            showFoneFthreecard: false,
            // 針對各個樓層
            showEachFloor: false,

            // 先設定add Button 是否顯現
            needAddButton: false,
            // 設定 ALL button
            needAllButton: false,
            // 設定 EAP button
            needEAPButton: false,
            // 設定 EQP button
            needEQPButton: false,
            // 設定 Switch button
            needSwitchButton: false,
            // 設定 alive_or_dead button
            needAlive_or_DaedButton: false,

            // 各 checkbox 的狀態
            checkboxes: {
                all: true,  // ALL
                eap: true,  // "EAP"
                eqp: true,  // "EQP"
                switch: true,   // "Switch"
                alive_or_dead: true //
            },

            // 初始顯示 "A/D"
            aliveOrDeadText: 'A/D',  
            // 儲存當前首要狀態
            buttonStats: {},

            // 匯入說明
            showmovein_detail: false,
            // 跳轉中繼站
            isRedirecting: false,

            // 展示可下載的全部資料
            showdownloadcard: false,

            // 全部的 csv 資料
            csvFiles: [],
            
            // 儲存要下載的 建築名稱(K11)...
            selectedBuilding: '',   

            // 回溯
            resource: false,

        }

    },
    computed: {
        // 總頁數
        totalPages() {
            return Math.ceil(this.cardData.length / this.pageSize);
        },

        // 當前頁數據
        paginatedData() {
            const startIndex = (this.currentPage - 1) * this.pageSize;
            const endIndex = startIndex + this.pageSize;
            return this.cardData.slice(startIndex, endIndex);
        },

        // 把每頁的數據分為 4 個表格，每個表格顯示 15 條數據
        groupedData() {
            const groups = [];
            let currentGroup = [];
            this.paginatedData.forEach((item, index) => {
                currentGroup.push(item);
                if (currentGroup.length === 15 || index === this.paginatedData.length - 1) {
                   groups.push(currentGroup);
                    currentGroup = [];
                }
            });
            return groups;
        },
        sortedEachFloor() {
            return Object.entries(this.eachfloor).map(([groupName, group]) => {
              const sortedGroup = Object.entries(group).sort((a, b) => {
                const floorA1 = parseInt(a[0].split('-')[0].slice(1)); // 提取 K 部分
                const floorB1 = parseInt(b[0].split('-')[0].slice(1)); // 提取 K 部分
                if (floorA1 !== floorB1) {
                  return floorA1 - floorB1; // 根據 K 部分排序
                }

                const floorA2 = parseInt(a[0].split('-')[1].slice(0, -1)); // 提取數字部分
                const floorB2 = parseInt(b[0].split('-')[1].slice(0, -1)); // 提取數字部分
                return floorA2 - floorB2; // 根據數字部分排序
              });

              return [groupName, Object.fromEntries(sortedGroup)];
            });
          },

          unwrappedEachFloor() {
            // 解包響應式資料，將其轉換為純資料結構
            return JSON.parse(JSON.stringify(this.eachfloor));
          },

          // 案建築分組
          groupByBuilding() {
            return this.csvFiles.reduce((groups, file) => {
              if (!groups[file.building]) {
                groups[file.building] = [];
              }
              groups[file.building].push(file);
              return groups;
            }, {});
          },

          // 根据 selectedBuilding 篩選建築資料
          filteredFiles() {
                // 如果沒有選擇，返回空值
            if (!this.selectedBuilding) {
              return [];
            }
            // 如果選擇棟別，返回該棟別的資訊
            return { [this.selectedBuilding]: this.groupByBuilding[this.selectedBuilding] };
          },

          groupByFloor() {
            return (files) => {
              return files.reduce((acc, file) => {
                (acc[file.floor] = acc[file.floor] || []).push(file);
                return acc;
              }, {});
            };
          }
    },

    destroyed() {
        // 清除監聽器
        window.removeEventListener('keydown', this.handleKeyDown);
    },

    async mounted(){
        this.username = localStorage.getItem("username") || sessionStorage.getItem("username");
        if (!this.username) {
            setTimeout(() => {
              window.location.href = "../lndex.html"; // 頁面跳轉
            }, 300);  // 延遲 0.3 秒跳轉
          }
        await this.fetchUnits();
        await this.get_suixiu_data_circle();
        await this.get_suixiu_EachFloor();
        window.addEventListener('keydown', this.handleKeyDown);
    },

    methods: {
        async showHome(){
            this.isSubSidebarVisible = false;
            this.showEAP_IPcard = false;
            this.showFoneFthreecard = true;
            this.showdownloadcard = false;
            this.showEachFloor = false;
            // 按鈕關閉
            this.needAddButton = false;
            this.needAllButton = false;
            this.needEAPButton = false;
            this.needEQPButton = false;
            this.needSwitchButton = false;
            this.needAlive_or_DaedButton = false;
            this.resource = false;
        },

        // sidebar 棟別
        async fetchUnits(){
            // show 出歲修的資料，暫時隱藏
            this.showtotalData = false;
            urls = `http://127.0.0.1:5000/get_unit`;
            try{
                const response = await fetch(urls);
                if(response.ok){
                    const data = await response.json();
                    this.unitfolders = data.folders || [];
                    // ✅ 過濾掉 alarm_store_files
                    this.unitfolders = (data.folders || []).filter(
                        folder => folder !== 'alarm_store_files'
                    );
                    console.log(this.unitfolders);
                }else{
                    console.log("無法正常取得棟別名稱")
                }
                }catch(error){
                console.log(`棟別取得錯誤: ` + error);
            }
        },

        // 選擇樓層之後輸出內容
        async fetchFloorfolders(folder){              
            try {
              const response = await fetch(`http://127.0.0.1:5000/get_floorfolders?folder=${folder}`);
              if (response.ok) {
                const data = await response.json();
                this.floorfolders = data.floorfolders || [];

                this.floorfolders.sort((a, b) => {
                    // 提取括號中的數字部分並進行比較
                    const numA = parseInt(a.match(/\((\d+)\)/)?.[1], 10);  // 提取括號中的數字
                    const numB = parseInt(b.match(/\((\d+)\)/)?.[1], 10);  // 提取括號中的數字
                    return numA - numB;  // 根據數字大小排序
                });

                // 輸出樓層轉 list 模式
                console.log(this.floorfolders);
              } else {
                console.error('Error fetching floorfolders');
              }
            } catch (error) {
              console.error('Request failed', error);
            }
        },

        // 顯示 樓層 - 區塊(區網)檔案名稱
        async fetchFloorBlockFiles(floorfolder){
            this.selectedFileFolder = floorfolder;
            console.log('this.selectedUnitName', this.selectedUnitName)
            console.log('this.selectedFileFolderName', this.selectedFileFolderName);
            try{
                if(this.selectedFileFolder === '其他'){
                    url = `http://127.0.0.1:5000/get_other`
                }else{
                    url = `http://127.0.0.1:5000/${this.selectedUnit}/${this.selectedFloor}/`
                }
                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    // 把這邊改成 list 形式
                    this.files = Array.isArray(data.files) ? data.files : []; 
                    // 輸出 list 的形式
                    console.log(this.files);
                } else {
                    console.error('Error fetching files');
                }
            }catch( error ){
                console.error('Request failed', error);
            }
        },

        // 針對 棟別
        async onUnitClick(unit){
            // 整張表先隱藏
            this.showEAP_IPcard
            // sidebar 側邊區塊在點擊的時候需要收起
            this.isSubSidebarVisible = false;
            // 如果從一開始 count_unit 沒有轉換成 true 的話，必須先轉換為 true
            if(this.press_unit === false){
                // 選擇棟別帶入
                this.selectedUnit = unit;
                // 輸出選擇的棟別
                console.log('選擇的棟別名稱: ', this.selectedUnit);

                await this.fetchFloorfolders(unit);
                              
                this.press_unit = true;
                this.selectedUnitName = unit;
            }else{
                // 如果已經為 true，則收回下拉式選單，這邊就改成 false
                this.press_unit = false;
                // 把 selectedUnit 變為空值即可
                this.selectedUnit = ''
                              
            }
            // 如果點了其他，則直接 show 其他的 card
            if(this.selectedUnit === "其他"){
                // 點其他之後會出現的輸出
                console.log('Unit: 其他');
                // 暫存 unit name
                this.selectedUnitName = unit;
                // 在這邊關閉ip卡片
                this.showEAP_IPcard = false;
                // 關閉F1/F3卡片
                this.showFoneFthreecard = false;
                // 在關閉所有樓層進度條卡片
                this.showEachFloor = false;
                // 點選其他後直接跳轉 樓層 - 區塊(區網)檔案名稱
                await this.fetchFloorBlockFiles(this.selectedUnit);
            }
        },
        // 點擊選擇棟別
        async onFloorfolderClick(floorfolder){
            // 選擇樓層帶入
            this.selectedFloor = floorfolder;
            // 一樣是暫存
            this.selectedFloorName = floorfolder
          // 輸出選擇的樓層
            console.log('選擇的樓層名稱: ',this.selectedFloor);
            // 選擇的 樓層 - 區塊(區網)檔案名稱
            await this.fetchFloorBlockFiles(floorfolder);

            // 重新點選時把資料收起
            this.showEAP_IPcard = false
        },

        // 關閉 顯示 樓層 - 區塊(區網)檔案名稱 的卡片
        async closePopup() {
            // 選擇的樓層 + 區網檔案名稱 改成空值
            this.selectedFileFolder = null;  
            // 放置 樓層 + 區網 或是 其他 區網(10)的檔案名稱也為空值
            this.files = []; 
            // 把 Unit 為空值
            this.selectedUnit = ''
            // 把樓層改為空值
            this.selectedFloor = ''
        },

        // 對區網所有的 data，包含其他
        async fetchAliveCardData(fileName){
            this.showEAP_IPcard = true;
            this.showFoneFthreecard = false;
            this.showEachFloor = false;
            this.selectedFileFolder = fileName;
            this.selectedFileFolderName = fileName;
            // 幾個按鈕顯示
            this.needAddButton = false,
            this.needAllButton = true,
            this.needEAPButton = true,
            this.needEQPButton = true,
            this.needSwitchButton = true,
            this.needAlive_or_DaedButton = true,
            this.resource = true,
            // 不顯示
            console.log(`selectedFileFolderName: ${this.selectedFileFolderName}`)
            try{
                let response;
                if (this.selectedFileFolder === "其他 區網(10)"){
                    this.needEQPButton = false
                    this.needSwitchButton = false
                    this.needAddButton = true
                    response = await fetch(`http://127.0.0.1:5000/show_another_data`);
                }else{
                    response = await fetch(`http://127.0.0.1:5000/${this.selectedUnitName}/${this.selectedFloor}/${this.selectedFileFolder}`);
                    console.log(`http://127.0.0.1:5000/${this.selectedUnitName}/${this.selectedFloor}/${this.selectedFileFolder}`)
                }
                if (response.ok) {
                    const rawData = await response.json();
                    // 確保 cardData 為空陣列
                    this.cardData = rawData || [];  
                    // this.cardData = rawData;
                    this.currentPage = 1;
                    const currentPage = this.currentPage;
                    this.currentPage = currentPage;
                    // console.log("fetchAliveCardData -> ", this.cardData);
                    this.selectedUnit = ''; 
                    this.selectedFileFolder = '';
                    this.startProgress(); 
                }else{
                    console.error('Failed to fetch data');
                    this.cardData = [];
                    }
                }catch(error){
                    console.error('Request failed', error);
                    this.cardData = [];
            }
            // 各 checkbox 的狀態
            this.checkboxes = {
                all: true,  // ALL
                eap: true,  // "EAP"
                eqp: true,  // "EQP"
                switch: true,   // "Switch"
                alive_or_dead: true //
            },
            
            // 初始顯示 "A/D"
            this.aliveOrDeadText = 'A/D'
            // 下載區塊
            this.showdownloadcard = false;
            // 匯入說明區塊
            this.showmovein_detail = false;
        },


        async backup(){
            console.log("Backup, this.selectedUnitName: ", this.selectedUnitName);
            console.log("Backup, this.selectedFloorName: ", this.selectedFloorName);
            console.log("Backup, this.selectedFileFolderName: ", this.selectedFileFolderName);
            try{
                if (!['歲修', '其他'].includes(this.selectedUnitName)) {
                    // 回傳給後台撈上一次的資料
                    response = await fetch(`http://127.0.0.1:5000/backup_simple/${this.selectedFileFolderName}`);
                    if(response.ok){
                        await this.fetchAliveCardData(this.selectedFileFolderName);
                    }else{
                        alert('備份無資料啦！')
                    }

                }else if(this.selectedUnitName == '其他'){
                    // 針對其他的回溯
                    response = await fetch(`http://127.0.0.1:5000/backup_another`);
                    if(response.ok){
                        await this.fetchAliveCardData(this.selectedFileFolderName);
                    }

                }else{
                    // 針對歲修的回溯
                    response = await fetch(`http://127.0.0.1:5000/backup_suixiu`);
                    if(response.ok){
                        await this.showsuixiualldata(this.currentPage);
                    }
                }

            }catch(error){
                console.error("備份過程中發生錯誤:", error);
                // 可以顯示錯誤訊息給使用者
                alert("備份失敗，請稍後再試或聯繫管理員。");
            }
            
        },

        async editStatus(item){
            console.log(item);
            this.currentItem = { ...item };
            this.isEditing = true;
            // 點選的當個 item
            console.log(this.currentItem);
        },

        // 取消編輯
        async cancelEdit() {
            window.addEventListener('keydown', this.handleKeyDown);
            this.isEditing = false;
            // 初始化
            this.currentItem = {
                ip: '',
                machine_id: '',
                local: '',
                Column_Position: '',
                device_name: '',
                tcp_port: '',
                com_port: '',
                os_spec: '',
                ip_source: '',
                category: '',
                online_test: '',
                set_time: '',
                remark: '',
                suixiu: '',
                file_place: '',
                status: ''
            };
        },

        // 增加按鈕異常先初始化...
        async add_New_suixiu_data(){
            // 初始化 currentItem
            this.currentItem = {
                ip: '',
                machine_id: '',
                local: '',
                Column_Position: '',
                device_name: '',
                tcp_port: '',
                com_port: '',
                os_spec: '',
                ip_source: '',
                category: '',
                online_test: '',
                set_time: '',
                remark: '',
                suixiu: 'Y'
            };
            this.isEditing = true;
            // 清除監聽器
            window.removeEventListener('keydown', this.handleKeyDown);
        },

        // 保存更改並發送到後端
        async saveStatus() {
            console.log("發送" + this.selectedFileFolder)
            if(this.currentItem.File_Place){
                this.currentItem.File_Place = this.currentItem.File_Place
                console.log("發送 - " + this.currentItem.File_Place)
            }
                // 保留當前頁碼
                const currentPage = this.currentPage;
                console.log("現在頁碼: ", currentPage);
                      
            try {
                // 修正
                console.log(this.selectedUnitName)
                if(this.selectedUnitName.startsWith("K")){
                    // 如果是 K11 8F 正常區網網段
                    url = `http://127.0.0.1:5000/update_single_place_status/${this.selectedUnitName}/${this.selectedFloorName}/${this.selectedFileFolderName}/${this.currentItem.ip}`;
                        console.log(url);
                }else if(this.selectedUnitName === "歲修"){
                    // 針對 其他 的 表
                    url = `http://127.0.0.1:5000/update_suixiu`;
                    console.log(url);
                }else{
                    url = `http://127.0.0.1:5000/update_other/${this.selectedUnitName}/${this.selectedFileFolderName}/${this.currentItem.device_name}`;
                    console.log(url);
                }
                // const response = await fetch(`http://127.0.0.1:5000/update-status/${this.selectedUnitFolderName}/${this.selectedFloorFolderName}/${this.selectedFileFolderName}/${this.currentItem.ip}`, {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ip: this.currentItem.ip,
                        machine_id: this.currentItem.machine_id,
                        local: this.currentItem.local,
                        Column_Position: this.currentItem.Column_Position,
                        device_name: this.currentItem.device_name,
                        tcp_port: this.currentItem.tcp_port,
                        com_port: this.currentItem.com_port,
                        os_spec: this.currentItem.os_spec,
                        ip_source: this.currentItem.ip_source,
                        category: this.currentItem.category,
                        online_test: this.currentItem.online_test,
                        set_time: this.currentItem.set_time,
                        remark: this.currentItem.remark,
                        suixiu: this.currentItem.suixiu,
                        file_place: this.currentItem.File_Place,
                        status: this.currentItem.status,
                        }),
                    }
                );
  
                if (!response.ok) {
                    throw new Error(`Failed to update status: ${response.status}`);
                }
  
                // 更新成功後，更新前端數據
                const index = this.cardData.findIndex(item => item.ip === this.currentItem.ip);
                if (index !== -1) {
                    this.cardData[index].status = this.currentItem.status;
                }
  
                // 退出編輯模式
                this.isEditing = false;
  
                // 初始化
                this.currentItem = {
                    ip: '',
                    machine_id: '',
                    local: '',
                    Column_Position: '',
                    device_name: '',
                    tcp_port: '',
                    com_port: '',
                    os_spec: '',
                    ip_source: '',
                    category: '',
                    online_test: '',
                    set_time: '',
                    remark: '',
                    suixiu: '',
                    file_place: '',
                    status: ''
                };
  
                // const currentPage = this.currentPage;  // 保持當前頁碼
                if(this.selectedUnitName !== "歲修"){
                    await this.fetchAliveCardData(this.selectedFileFolderName);

                }else{
                    console.log('this.selectedUnitName: ', this.selectedUnitName)
                    this.showsuixiualldata(this.currentPage)
                    
                }
                      
                // 保持頁碼
                this.$nextTick(() => {
                    this.currentPage = currentPage;
                });
                window.addEventListener('keydown', this.handleKeyDown);
                
                } catch (error) {
                console.error('Error saving status:', error);
            }
        },


        async toggleSuixiu(){
            const result = await Swal.fire({
                title: '選擇操作',
                text: '請選擇要執行的功能：',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#28a745',
                confirmButtonText: '歲修看板',
                cancelButtonText: '維護資料',
                showCloseButton: true,
                allowOutsideClick: false
            });

            if (result.isConfirmed) {
                // 用戶選擇歲修看板 - 跳轉到 lab.html
                localStorage.setItem('username', this.username);
                window.location.href = "lab.html";
            } else if (result.isDismissed && result.dismiss === Swal.DismissReason.cancel) {
                // 用戶選擇維護資料 - 執行原有功能
                // 切換右側子側邊欄顯示
                this.isSubSidebarVisible = !this.isSubSidebarVisible;
                // 刪除右側圖表
                this.showEAP_IPcard = false;
                // 刪除F1/F3
                this.showFoneFthreecard = false;
                // 屏蔽各樓層資料
                this.showEachFloor = false;
                // 屏蔽每個 button
                this.needAddButton = false
                // 設定 ALL button
                this.needAllButton = false
                // 設定 EAP button
                this.needEAPButton = false
                // 設定 EQP button
                this.needEQPButton = false
                // 設定 Switch button
                this.needSwitchButton = false
                // 設定 alive_or_dead button
                this.needAlive_or_DaedButton = false
            }
            // 如果用戶點擊關閉按鈕或按 ESC，什麼都不做
        },
        // show 歲修那張表
        async showsuixiualldata(page){
            this.isSubSidebarVisible = false;
            this.showEAP_IPcard = true;
            this.showFoneFthreecard = false;
            this.showEachFloor = false;
            this.selectedUnitName = "歲修"
            this.showdownloadcard = false;
            this.showmovein_detail = false;

            // 新增按鈕
            this.needAddButton = true;
            // 回溯按鈕
            this.resource = true;
            // 所有按鈕
            this.needAllButton = true;
            // eap 按鈕
            this.needEAPButton = true;
            // eqp 按鈕
            this.needEQPButton = false;
            // Switch 按鈕
            this.needSwitchButton = false;
            // alive_or_dead 按鈕
            this.needAlive_or_DaedButton = true;

            try{
                const response = await fetch(`http://127.0.0.1:5000/show_suixiu_card`);
                if (response.ok) {
                  const rawData = await response.json();
                  this.cardData = rawData || [];  // 確保 cardData 為空陣列
                  // this.cardData = rawData;
                  this.currentPage = page;
                  console.log("this.cardData: ", this.cardData);
                  this.selectedFileFolder = '';  
                  }else{
                    console.error('Error fetching file content');
                }
            }
            catch(error){
                console.error('Request failed', error);
                this.cardData = [];
            }   
            await this.startProgress();
            // 預防資訊錯亂
            this.selectedFloorName = ''
        },

        // 登入時自動取得歲修用資訊
        async get_suixiu_data_circle(){
            this.showFoneFthreecard = true;
            try {
                    const response = await fetch('http://127.0.0.1:5000/get_suixiu_circle_data');
                    if (response.ok) {
                        const data = await response.json();
                        console.log(`這邊自動取得歲修資料`, data)
                        this.F1_EAP_Success_Rate = data.total_data["F1"]["Percent"]
                        this.F3_EAP_Success_Rate = data.total_data["F3"]["Percent"]
                        this.F5_EAP_Success_Rate = data.total_data["F5"]["Percent"]
                        try{
                            this.ip_Success_Rate = data.total_data["歲修"]["ip_len"]
                            this.EAP_Success_Rate = data.total_data["歲修"]["ping_device"]
                            this.targetProgress1 = parseFloat(data.total_data["歲修"]["ip_use_percent"]);
                            this.targetProgress2 = parseFloat(data.total_data["歲修"]["ping_device_percent"]);
                        }catch(error){
                            this.ip_Success_Rate = data.total_data["suixiu"]["ip_len"]
                            this.EAP_Success_Rate = data.total_data["suixiu"]["ping_device"]
                            this.targetProgress1 = parseFloat(data.total_data["suixiu"]["ip_use_percent"]);
                            this.targetProgress2 = parseFloat(data.total_data["suixiu"]["ping_device_percent"]);
                        }
                        this.startProgress();
                    } else {
                        console.error('Error fetching folders');
                    }
            } catch (error) {
                console.error('Request failed', error);
            }
        },

        // 登入時自動取得歲修各樓層資訊
        async get_suixiu_EachFloor(){
            try {
                const response = await fetch('http://127.0.0.1:5000/get_suixiu_EachFloor');
                if (response.ok) {
                    const result = await response.json();
                    // console.log("result: " + result);
                    this.eachfloor = result.eachfloor;
                    console.log(this.eachfloor)
                } else {
                    console.error('Error fetching folders');
                    }
                } catch (error) {
                    console.error('Request failed', error);
            }
        },

        getProgressStatus(percentage) {
            if (percentage <= 30) {
                return '#FF4D4F'; // 紅色
            } else if (percentage > 30 && percentage <= 75) {
                return '#FA8C16'; // 橙色
            } else {
                return 'rgb(92, 184, 122)' // 綠色
            }
        },
          
        // 開始進度條的增長動畫
        async startProgress() {
            try{
                const Data = {};
                let url = '';
                if(this.selectedUnitName.startsWith("K")){
                    url = `http://127.0.0.1:5000/get_progress_data/${this.selectedFileFolderName}`
                
                }else if(this.selectedUnitName === "其他"){
                    url = `http://127.0.0.1:5000/get_other_status_data`
                }else{
                    this.selectedFileFolderName = "suixiu"
                    url = `http://127.0.0.1:5000/get_suixiu_status`
                }

                console.log("startProgress ->" + url)

                response = await fetch(url);
                if (response.ok) {
                    const status_data = await response.json();
                    console.log("status_data -> ", status_data)

                    // 這邊出問題
                    // 這會是包含 "ip_len", "ip_use_percent" 等的對象
                    const Data = status_data[this.selectedFileFolderName];  
                    const ipLen = Data.ip_len;  // "383 / 383"
                    const ipUsePercent = Data.ip_use_percent;  // "94.25"

                    const pingDevice = Data.ping_device;  // "383 / 383"
                    const pingDevicePercent = Data.ping_device_percent;  // "98"

                    const EAPLen = Data.eqp_len;
                    const EAPDevicePercent = Data.eqp_len_percent;

                    const SwitchLen = Data.switch_len;
                    const SwitchDevicePercent = Data.switch_len_percent;

                    this.ip_Success_Rate = ipLen;
                    this.EAP_Success_Rate = pingDevice;
                    this.EQP_Success_Rate = EAPLen;
                    this.Switch_Success_Rate = SwitchLen;

                    this.targetProgress1 = parseFloat(ipUsePercent);
                    this.targetProgress2 = parseFloat(pingDevicePercent);
                    this.targetProgress3 = parseFloat(EAPDevicePercent);
                    this.targetProgress4 = parseFloat(SwitchDevicePercent);

                } else {
                    console.error('Error fetching files');
                }
            }catch(error){
              console.error('Error fetching files');
            }

            this.progressBar1 = 0;
            this.progressBar2 = 0;
            this.progressBar3 = 0;
            this.progressBar4 = 0;


            const interval1 = setInterval(() => {
                if (this.progressBar1 < this.targetProgress1) {
                    this.progressBar1 += 1; // 每次增加 1
                } else {
                    clearInterval(interval1); // 停止增長
                }
            }, 20); // 每 50 毫秒更新一次

            // 進度條 2 的增長
            const interval2 = setInterval(() => {
                if (this.progressBar2 < this.targetProgress2) {
                    this.progressBar2 += 1; // 每次增加 1
                } else {
                    clearInterval(interval2); // 停止增長
                }
            }, 20); // 每 50 毫秒更新一次

            // 進度條 3 的增長
            const interval3 = setInterval(() => {
                if (this.progressBar3 < this.targetProgress3) {
                    this.progressBar3 += 1; // 每次增加 1
                } else {
                    clearInterval(interval3); // 停止增長
                }
            }, 20); // 每 50 毫秒更新一次

            // 進度條 4 的增長
            const interval4 = setInterval(() => {
                if (this.progressBar4 < this.targetProgress4) {
                    this.progressBar4 += 1; // 每次增加 1
                } else {
                    clearInterval(interval4); // 停止增長
                }
            }, 20); // 每 50 毫秒更新一次
        },

        async toggleCheckbox(button) {
            // 切換當前按鈕的選取狀態，不影響其他按鈕
            this.checkboxes[button] = !this.checkboxes[button];


            if(button === "all" && this.checkboxes.all){
              this.checkboxes.eap = true;
              this.checkboxes.eqp = true;
              this.checkboxes.switch = true;
              this.checkboxes.alive_or_dead = true;
              this.aliveOrDeadText = "A/D"
            }

          
            if(button === "alive_or_dead"){
              this.aliveOrDeadText = this.checkboxes.alive_or_dead ? 'A' : 'D';
            }

            console.log(this.checkboxes)

            await this.sendButtonStateToBackend();
          },

          async sendButtonStateToBackend(){
            // console.log(this.checkboxes)
            console.log(this.selectedUnitName);
            
            if(this.showmovein_detail){
              return
            }

            if(this.showdownloadcard){
              return
            }

            let url = '';
            if(this.selectedUnitName.startsWith("K")){
              url = `http://127.0.0.1:5000/select_Button_data/${this.selectedUnitName}/${this.selectedFloorName}/${this.selectedFileFolderName}`;
              console.log(url)
            }else if(this.selectedUnitName === "其他"){
              url = `http://127.0.0.1:5000/select_Another_button/${this.selectedUnitName}/${this.selectedFileFolderName}`;  
              console.log(url)
            }else{
              url = `http://127.0.0.1:5000/select_suixiu_button`;  
              console.log(url)
            }
            
            try {
            const response = await fetch(url, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                buttonStats: this.checkboxes,  // 將目前的checkbox狀態傳送到後端
                aliveOrDeadText: this.aliveOrDeadText
              }),
            });

            if (response.ok) {

              const rawData = await response.json();
              // 確保 cardData 為空陣列
              this.cardData = Array.isArray(rawData) ? rawData : [];
              console.log(this.cardData)
              // this.cardData = rawData;
              this.currentPage = 1;
              this.showEAP_IPcard = true;
            }
          } catch (error) {
              console.error('發送請求時發生錯誤:', error);
            }
        },

        async resetdata(){
            // console.log("this.selectedUnitName: ", this.selectedUnitName)
            // console.log("this.selectedFloorName: ", this.selectedFloorName)
            // console.log("this.selectedFileFolderName" , this.selectedFileFolderName)
            if (this.selectedFloorName !== "其他 區網(10)" && this.selectedFileFolderName !== "suixiu") {
                await this.fetchAliveCardData(this.selectedFileFolderName);
            } else if (this.selectedFloorName === "其他 區網(10)") {
                await this.fetchAliveCardData(this.selectedFileFolderName);
                this.needAddButton = true;
            } else {
                await this.showsuixiualldata(1);
            }
            
        },

        // 取得所有的檔案名稱
        async fetchCsvFiles(){
            try {
                const response = await fetch('http://127.0.0.1:5000/get_csv_files');
                if (!response.ok) {
                    throw new Error('Failed to fetch CSV files');
                }
                              
                const data = await response.json();
                console.log('CSV files:', data.csv_files);
                this.csvFiles = data.csv_files;  // 這裡會保存後端傳回的檔案資料
            } catch (error) {
                console.error('Error:', error);
            }
        },
          
        async sortFiles() {
            //對 this.csvFiles 這個區塊進行排序
            this.csvFiles.sort((a, b) => {
                // 判断是否為K開頭
                const isKBuildingA = a.building.startsWith('K');
                const isKBuildingB = b.building.startsWith('K');
                // 如果不是就放在其他地方
                if (!isKBuildingA) a.building = '其他';
                if (!isKBuildingB) b.building = '其他';
          
                // 如果兩個建築都是K開頭或都不是K開頭，按建築和樓層排序
                if (isKBuildingA === isKBuildingB) {
                    const buildingNumberA = a.building !== '其他' ? parseInt(a.building.match(/\d+/)?.[0]) : Infinity;
                    const buildingNumberB = b.building !== '其他' ? parseInt(b.building.match(/\d+/)?.[0]) : Infinity;
          
                    const floorNumberA = a.floor ? parseInt(a.floor.match(/\d+/)[0]) : Infinity;
                    const floorNumberB = b.floor ? parseInt(b.floor.match(/\d+/)[0]) : Infinity;
          
                    if (buildingNumberA === buildingNumberB) {
                        return floorNumberA - floorNumberB;
                    }
                    return buildingNumberA - buildingNumberB;
                }
          
                // 如果只有A是K開頭，A排在前面
                if (isKBuildingA && !isKBuildingB) return -1;
                if (!isKBuildingA && isKBuildingB) return 1;
          
                return 0;
            });
            // 如果是 suixiu，改成歲修
            this.csvFiles.forEach(file => {
            if (file.file_name === 'suixiu') {
                file.file_name = '歲修';
                }
            });
        },

        async show_movein() {
            // 上傳格式說明顯示
            this.showmovein_detail = true;
            // show ip 表的卡關閉
            this.showEAP_IPcard = false
            // f1f3表關閉
            this.showFoneFthreecard = false;
            // 各樓層狀態便
            this.showEachFloor = false;
            // 側邊欄關閉
            this.isSubSidebarVisible = false;
            // 關閉下載區塊
            this.showdownloadcard = false;
            //  跳轉中繼站
            this.isRedirecting = true;
            setTimeout(() => {
                localStorage.setItem('username', this.username);
                window.location.href = "update.html"; // 頁面跳轉
            }, 100);  // 延遲 0.3 秒跳轉
        },


        async show_moveout() {
            await this.showtotalDataButton();
            await this.showEachFloordataButton();
            await this.fetchCsvFiles();
            await this.sortFiles();
            this.showFoneFthreecard = false;
            this.showEAP_IPcard = false;
            this.showEachFloor = false;
            this.showdownloadcard = true;
            // 匯入說明區塊
            this.showmovein_detail = false;
        },
        

          async downloadFile(file_name, file_path){
            console.log(`http://127.0.0.1:5000/download/${file_name}`)
            try{
              const response = await fetch(`http://127.0.0.1:5000/download/${file_name}`, {
                method: 'GET',
                headers: {
                  'Content-Type': 'application/json',
                },
              });
              if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status}`);
              }

              const blob = await response.blob();

              const link = document.createElement('a');
              link.href = URL.createObjectURL(blob);
              if(file_name === "歲修"){
                link.download = `${file_name}_(Security C).xlsx`; 
              }else{
                link.download = `${file_name}_(Security C).csv`; 
              }
              link.click();

              URL.revokeObjectURL(link.href);

            }catch (error) {
              console.error('下载失败:', error);
            }
          },

          
          async downloadAllFiles(){
            try{
              const response = await fetch(`http://127.0.0.1:5000/downloadAllFiles`, {
                method: 'GET',
                headers: {
                  'Content-Type': 'application/json',
                },
              });
              if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.status}`);
              }

              // 假設返回的是文件流（Blob）
              const blob = await response.blob();

              const link = document.createElement('a');
              link.href = URL.createObjectURL(blob);
              // 把資料投放成 zip
              link.download = `IP表備份統整_(Security C).zip`; 
              link.click();
              
              // 釋放 URL 物件
              URL.revokeObjectURL(link.href);

            }catch (error) {
              console.error('下载失败:', error);
            }
        },


        // 歲修用的資料，查看總表 -> f1 + f3
        async showtotalDataButton(){
            this.isSubSidebarVisible = false;
            this.showEAP_IPcard = false;
            this.showFoneFthreecard = true;
            this.showEachFloor = false;
            // 按鈕關閉
            this.needAddButton = false;
            this.resource = false;
            this.needAllButton = false;
            this.needEAPButton = false;
            this.needEQPButton = false;
            this.needSwitchButton = false;
            this.needAlive_or_DaedButton = false;
            // 下載東西的區塊
            this.showdownloadcard = false;
        },

        async showEachFloordataButton(){
            this.isSubSidebarVisible = false;
            this.showEAP_IPcard = false;
            this.showEachFloor = true;
            this.showFoneFthreecard = false
            // 按鈕關閉
            this.needAddButton = false;
            this.resource = false;
            this.needAllButton = false;
            this.needEAPButton = false;
            this.needEQPButton = false;
            this.needSwitchButton = false;
            this.needAlive_or_DaedButton = false;
            // 下載東西的區塊
            this.showdownloadcard = false;
        },

        // 前一頁
        prevPage() {
            this.currentPage = (this.currentPage - 2 + this.totalPages) % this.totalPages + 1;
        },
          
        // 下一頁
        nextPage() {
            this.currentPage = (this.currentPage % this.totalPages) + 1;
        },
          
        // 鍵盤左右鍵
        handleKeyDown(event) {
            if (event.key === 'ArrowLeft') {
                this.prevPage(); // 左箭頭，上一頁
            } else if (event.key === 'ArrowRight') {
                this.nextPage(); // 右箭頭，下一頁
            }
        },
          
    }


});


app.mount('#app');

// 資料庫轉拋?