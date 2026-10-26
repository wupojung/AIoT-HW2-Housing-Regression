# Issue #26 工程回顧：保留經驗，簡化下一輪

**結案分類（Owner 指示）：** `CLOSED / NOT PLANNED`，原因 `SUPERSEDED BY HOMEWORK 2 RECOVERY STRATEGY`。這是優先順序與範圍調整，**不是 macOS Supervisor 技術驗收 PASS，也不是 launchd／Watchdog 已被證明不可行**。Issue 會在最終結案留言後依授權關閉。

本回顧由 W1P1、W1P2、Independent High QA 各自獨立起草後彙整。標記意義：**OBSERVED** 為有紀錄支持的事實；**INFERRED** 為根據事實的解讀；**UNKNOWN** 為尚未驗證；**RECOMMENDATION** 為下一輪建議。這份文件不重啟 #26，也不授權 Single-Worker 實作或研究執行。

## 1. 原始目標與實際範圍

- **OBSERVED：** Issue #26 原本要為已合併的 Windows A2 bounded Runner 設計 macOS 後端，同時保留 Windows Job Object 行為。Owner 後續批准 M0–M5 順序；M0 通訊與環境準備 PASS，M1 三版設計後由 High QA 靜態審查 PASS。M1 PASS 只表示設計符合當時 Gate，不代表 macOS Runner 已實作或通過執行測試。[M0 通訊記錄](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6400759538)、[M0–M5 計畫](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6400819309)、[M1 PASS](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6401004454)
- **OBSERVED：** Windows A2 已由 [PR #25](https://github.com/wupojung/AIoT-HW2-Housing-Regression/pull/25) 合併，merge commit 為 `3ea596d5f1a449015fd2816619405f23574a6923`。PR 描述記錄 bounded synthetic suite 27/27 PASS 與獨立 QA PASS。這是 Windows 路徑證據，不能當作 macOS Runner 或 macOS PoC PASS。
- **OBSERVED：** M2 首次可行性工作遇到 process-only Probe 的身分競態，未完成 READY；後續恢復紀錄保存了對該特定 Worker／Child 的身分核驗與清理結果。此歷史 Probe 不等同後來設計的 launchd PoC。
- **OBSERVED：** M2 先後涵蓋原生 macOS 合約、Watchdog-first、launchd 補充研究，以及 launchd + Watchdog + Runner + Worker 架構 PoC。Watchdog 設計 QA BLOCKED；launchd 補充審查 NEEDS PROOF；PoC v1 事前 QA BLOCKED；v2 將 P03/P04 撤回為 NOT RUN，P07 縮小為循序 replay。P01–P08 均未實測，未建立或啟動 launchd Job。[Watchdog Gate](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6405116786)、[PoC 結果](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6405759167)
- **OBSERVED：** Owner 最後依 Homework 2 時程停止 macOS Supervisor 研究，指定新方向為 Single Worker、五種新版 Feature Selection、3-fold CV 與一次性 sealed Holdout。[Owner 結案交接](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6406077095)

## 2. 重要技術決策時間線

| 階段 | 結果 | 證據解讀 |
|---|---|---|
| M0 | PASS | 完成三 Agent 通訊往返與最小環境確認；不是 Runner 驗收。 |
| M1 | DESIGN PASS | 第三版設計與 High QA 靜態審查通過；沒有執行 Probe。 |
| M2 初次可行性 | BLOCKED | process-only Probe 在 READY 前碰到身分競態；記憶體案例未執行。其後有界恢復清理只涵蓋該次已核驗的程序。 |
| 原生 macOS 安全合約 | BLOCKED | 設計仍未證明程序族群清理、記憶體範圍與失敗恢復。 |
| Watchdog-first | BLOCKED | Controller 遺失時無法保證 Worker 有限停止；程序後代及 PID 安全終止條件未定。 |
| launchd 補充研究 | NEEDS PROOF | 文件所述 `AbandonProcessGroup` 涵蓋同 PGID 剩餘程序，沒有證明程序群組對本工作獨佔或涵蓋所有脫離群組的後代。 |
| 架構 PoC | PARTIAL 設計；未執行 | P03 無法證明同 PGID 僅含 PoC 程序；P04 沒有獨立有限的 pre-entry 失敗回收界線。P01–P08 全部 NOT RUN。 |
| 最終決策 | NOT PLANNED | Owner 取消 #26 作為 HW2 交件前置；不是技術 PASS，也不是一次已執行但失敗的 PoC。 |

**OBSERVED：** PoC High QA v1 指出 P03 的 same-PGID 清理可能碰到無關程序，以及 P04 的 6 秒恢復準則與 10 秒 `ThrottleInterval` 不符；`ThrottleInterval` 是啟動節流，不是重試次數上限。v2 明確撤回這兩個案例而不是冒險執行，High QA 因此判定沒有任何 case 在當時授權下可執行。私有證據摘要：PoC v1 設計 SHA-256 `dd44b6b5581d723b80e31a0d1ed3015539eaa03ac186a2460782739287868461`、QA v1 `59f7ba410814a1f63406a0a9b317a4e19706e02fd1d0b2cffc323b3bcb5f3843`、v2 設計 `0042feb8e5a39765a43641bcdb82eee61799ca246e8e3bec952a669eb5419722`、QA v2 `350bcbb121ac506dd069e8aeaccb9abd5d7321092d2e0980dd0e8dc102751cb6`。完整 Handoff 與檔案雜湊留在 ignored `local/`，不隨本文件公開。

## 3. 三方回顧：共同結論與不同觀察

### W1P1 Coordinator：範圍與協調

- **OBSERVED：** 需求由跨平台 macOS 後端，逐步擴及 Windows Job Object 記憶體指標、程序後代管理、Watchdog、launchd、KeepAlive、雙向 Heartbeat、generation/replay 和 teardown。
- **INFERRED：** 專案將未來 Production Runner 的完整隔離要求提前作為 HW2 單次研究執行的前置條件；再加上平台方向數次調整，使團隊投入多輪設計，卻尚未能啟動架構 PoC。
- **OBSERVED：** Handoff、ACK、UTF-8 byte count 和 SHA-256 有效降低長訊息截斷與版本混淆；Herdr 的 `agent_prompted` 只表示送達，不代表接收、完成或 QA 通過。
- **RECOMMENDATION：** 兩輪相同根因的 QA BLOCKED 後，Coordinator 必須啟動 Scope／Acceptance Review，讓 PM 在修需求、縮範圍、接受明示限制或停止之間作決定；不得只派下一輪修改。

### W1P2 Implementer：架構與工程

- **OBSERVED：** Windows `p4b_job.py` 使用 Job Object 管理受控程序、Job memory limit 和 kill-on-close；macOS 的 POSIX process group 是群組關係，不是同一種擁有型 Job 物件。launchd `AbandonProcessGroup` 針對同 PGID 剩餘程序；psutil/RSS 監控只能提供觀測，不是核心層級整組 RAM 硬上限。官方參考：[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)、[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)、[Apple launchd.plist(5)](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5)、[Apple launchctl(1)](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchctl.1)。
- **OBSERVED：** 架構 PoC 從未執行；設計 v1 將正常生命週期、異常退出、重啟、重播與撤銷放入同一矩陣，後續因 P03/P04 邊界無法證明而停止。
- **INFERRED：** 兩個 Supervisor Job 加 Runner、Worker、Heartbeat、restart state 和 teardown，比目前課程需要的串行單工作者路徑複雜；先實作完整 Supervisor 增加了尚未被作業需求證明的失敗模式。
- **RECOMMENDATION：** 保留已合併的 Windows A2 實作與合成測試、checkpoint/provenance、安全錯誤輸出等經驗。未來若取得新授權，先以單一 Worker、固定 argv、序列執行和小型合成任務建立最小可觀察路徑；不預先新增常駐 Watchdog 或 launchd Job。

### Independent High QA：品質與驗收

- **OBSERVED：** 阻擋 P03/P04 是必要的：same-PGID 清理邊界可能涵蓋無關程序；pre-entry 啟動錯誤沒有獨立有限回收者。v2 正確將這兩者標為 NOT RUN，而不是宣稱測試失敗。
- **OBSERVED：** QA v2 將整體說明收斂為「安全子集可設計，但完整核心案例 PoC 不可行」；P07 併發鎖主張因 `kickstart` 行為未證明而縮為循序 replay。沒有把缺少 RAM 硬上限誤稱為 PoC 執行失敗。
- **RECOMMENDATION：** PoC Feasibility QA 應問某個明確合成案例能否在有限範圍安全顯示行為；Research Correctness QA 應查資料隔離、fold-local fit、指標與重現性；Production Safety QA 才驗收實際部署的服務生命週期、完整資源控制、權限及復原。三種 QA 不可混成同一門檻。
- **RECOMMENDATION：** 先把測試拆為不具破壞性的觀察案例，再依風險升級；P08 teardown 只能附屬於已建立的測試 Job，不能當成獨立清理證據。QA 每次應列出精確案例、阻擋項及哪些屬於限制，而非把一個阻擋推廣成所有案例都不安全。

## 4. 範圍膨脹與管理轉折

- **OBSERVED：** 最初安全契約要求 macOS 證明與 Windows Job Object 相近的整組記憶體與子程序保護；Owner 後來澄清目標是可控地執行 Python，並允許不同計量方式，之後優先指定 Python Watchdog，再以 launchd 為補充，最後又允許一個限定的 launchd 架構 PoC。這些是不同階段的正式決策，不應被回寫成同一組穩定需求。
- **INFERRED：** PM scope reduction 發生得太晚。其間 QA 依當時正式驗收條件阻擋真實風險，工程端則繼續增加設計細節；這不是個別 Agent 的責任，而是需求、實驗必要性和 Production Safety Gate 未及時分開。
- **OBSERVED：** 初版架構 PoC Owner 註明「QA 核可後」可建立臨時 Jobs；v2 Handoff/複審流程後來又加入「另需 Owner runtime 授權」的說法。該額外確認沒有改變 P03/P04 已阻擋、後續也被結案決策停止的事實，但顯示 Coordinator 應逐字維持授權邊界，不應自行加嚴或放寬。
- **RECOMMENDATION：** 在發派前以一頁凍結「研究要回答的問題、案例是否關鍵、允許的限制、可接受的已知風險、STOP 條件、QA 層級、授權來源」。如果安全案例不可證明，先回報 PM 做 scope decision，而不是自然擴大成更完整的 Supervisor 架構。

## 5. QA 的三種門檻

| QA 層級 | 要回答的問題 | 合適證據 | 不應自動要求 |
|---|---|---|---|
| **Feasibility** | 指定機制能否完成一個明確、有限的合成任務？ | 精確版本/設定、最小合成輸入、觀察事件、結果與 STOP/回復條件 | 完整部署認證、所有未來子孫程序情境、未被該 PoC 要求的跨平台等效指標 |
| **Research Correctness** | 結果是否由正確分割、無洩漏流程與可重現設定產生？ | fold manifest、fit 邊界、資料/程式/設定摘要、重現結果、Holdout 使用紀錄 | Production 常駐服務或作業系統級強制記憶體界線，除非研究運算確實要求 |
| **Production Safety** | 部署後能否在支援環境中維持資源、權限、程序與復原保證？ | 目標主機驗收、錯誤/壓力/復原、硬限制/讀回、操作與事故方案 | 不能以一次小型 PoC PASS 代替正式的長期營運驗收 |

**RECOMMENDATION：** 每個 Gate 的標籤應精確反映驗收種類；`DESIGN PASS`、`QA-REVIEWED`、`QA-EXECUTED`、`RUNTIME PASS` 和 `PRODUCTION READY` 必須各自分開記錄。

## 6. Homework 2 Single-Worker 交接建議

- **OBSERVED：** Owner 結案策略指定 Single Worker 串行研究；新版五種方法為 Pearson、Mutual Information、Lasso、ElasticNet、Ridge RFE；採 3-fold CV，最後對 sealed Holdout 一次性評估。原始候選輸入特徵至少 14 的要求指可用原始特徵，不是最終選出的 feature 數；編碼後欄位另行計數。[Owner 結案交接](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6406077095)
- **RECOMMENDATION：** 新 Issue 先凍結小型 synthetic acceptance，再由 Owner/PM 凍結正式研究協定。Single Worker 一次只處理一個 fold/task；輸出保存在私有位置，記錄 run ID、輸入摘要、程式與環境版本、seed、fold assignment、方法參數、結果、失敗狀態及 checkpoint；不需要透過 Agent/LLM 執行每次模型 fit。
- **RECOMMENDATION：** Leakage Prevention：每個 fold 的 imputation、encoding、scaling、feature selection 和 tuning 只能在該 fold training partition fit；validation 僅用來評估。ID 與 target 不作 predictor。不同 fold 的 encoded schema 應以 fold-local 規則記錄，不能先在全資料 fit transform。
- **RECOMMENDATION：** Reproducibility：固定並記錄 3-fold 切分、seed、依賴版本、方法設定及 code/data digest；checkpoint 僅能對完全相符的 run resume；每個結果可追溯到單一 fold 與設定。
- **RECOMMENDATION：** Holdout 保持密封，不能參與方法、特徵數或超參數選擇；所有 CV 決策完成後才一次性評估，報告清楚區分 CV 分數與一次性 Holdout 結果。
- **UNKNOWN：** 新五方法的確切 API、特徵選擇單位與 K 規則、比較估計器、3-fold protocol 細節與 Holdout 報告格式尚待新 Issue/Owner/Cloud PM 正式決定。不得把 #22 舊 protocol 當成新版規格，也不得在本回顧中更新 #21/#22/#23。
- **RECOMMENDATION：** 本輪只完成流程經驗交接；任何資料讀取、真實模型實驗、Single-Worker 開發都須依新 Issue 及獨立授權啟動。

## 7. 值得保留與應簡化的成果

### 保留

- **OBSERVED：** Windows A2 Job Object 實作、其 Windows synthetic tests 與 PR #25/merge evidence；不改寫、不以 macOS 設計證據取代。
- **OBSERVED：** M0/M1 記錄、M2 早期有界 process-only Probe 的復原紀錄、所有 Watchdog/launchd 設計版本、QA 結果、PoC v1/v2 與 manifest。PoC v1/v2 是設計及 QA 證據，不是可直接投入正式 Runner 的程式。
- **RECOMMENDATION：** 保留 fail-closed、明確 timeout、可重現切分、私有/公開輸出隔離、checkpoint identity 檢查、合成測試與事件化 Handoff 等真正對應風險的做法。

### 簡化

- **RECOMMENDATION：** 在作業需求未要求多程序時，不先建立 OS Adapter、Watchdog、launchd job、process-group kill、父子孫程序監督或自動重啟架構。
- **RECOMMENDATION：** 只設需要的最小並行數（Single Worker 即 1），以有限 wall timeout 和明確停止條件控管單次任務；若無法保證系統級硬記憶體界線，清楚記錄 best-effort/已知限制並交 PM 判斷，而非宣稱具備硬限制。
- **RECOMMENDATION：** 不重複核對未變更的手冊、Pane、長歷史；一份完整 Handoff、一份 ACK、一個完成結果、一份 QA delta 即可。Coordinator 作唯一公開 Issue 報告窗口。

## 8. 未解決問題與移交

- **UNKNOWN：** 這次有限目錄盤點未找到 Owner 所提 P4-A 私有 archive；未刪除或移動任何相關內容。PR #25 與 Git remote branch refs 保留，但它們不能證明私有 archive 的位置或完整性。後續使用任何 P4-A archive 前，需先由 Owner/Cloud PM 指明其所在地並確認完整性。
- **UNKNOWN：** 本次未查詢全主機程序表；歷史回復紀錄只證明那次特定 synthetic probe 的兩個程序已被核驗清理。launchd PoC 沒有建立 Job 或啟動程序；不宣稱未知的無關主機程序狀態。
- **OBSERVED：** 唯讀 Worktree inventory 只列出 main Checkout 一個工作樹；本地分支只有 `main`，多個 `origin/*` refs 保持不變；沒有符合 CLEANABLE 條件的工作樹。此次無 Worktree 或 Branch 被移除。
- **RECOMMENDATION：** 下一個 Homework 2 專案另開 Owner 指定的新 Issue；只攜帶本回顧的簡化原則、Windows A2 已合併能力與必要的研究正確性契約，不帶入 #26 的 Supervisor 實作任務。任何後續 macOS Supervisor 研究另需明確的新授權。

## 9. Next Project Guardrails

1. **交件優先：** 課程交件需求優先於非必要平台工程。
2. **需求連結：** 每個新增 Gate 都要指出實際需求、可能損害與可驗收證據。
3. **先小型驗證：** 用最小合成實驗驗證關鍵假設，再決定是否擴充架構。
4. **拆開 QA：** Feasibility、Research Correctness、Production Safety 分別制定 Gate，不互相代替。
5. **有界探索：** 正式 Production 規格未達成，不自動否決已授權的有限探索；先判斷風險是否能被隔離並明記限制。
6. **兩輪轉向：** 同一根因連續兩輪 QA BLOCKED，Coordinator 必須停止下游工作並啟動 Scope/Acceptance Review。
7. **證據不丟失：** Handoff、Logs、QA、Checkpoint、私人資料及安全 Ref 不因策略修改刪除；每份封存列入 byte count 與 SHA-256 manifest。
8. **不假設等效：** Windows 與 macOS 可採不同後端；保留 Windows A2 契約，不把單一平台測試宣稱為跨平台 PASS。
9. **保護 Holdout：** Holdout 不用於方法/特徵數/超參數選擇，只在授權的一次性最終評估使用。
10. **低成本協作：** 一個 Agent 一個 scope；Herdr 只傳短訊和檔案位置；ACK 表示收到，完成必須另有 completion Handoff；Coordinator 做唯一外部回報，不以反覆輪詢補足訊息。
11. **不擴充凍結規格：** #21/#22/#23 依正式變更程序維持凍結；本回顧不建立 Issue、不開始實驗、不授權 Merge。

## 10. 證據索引與限制

- **OBSERVED：** 公開決策時間線見 #26 comments [6400819309](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6400819309)、[6401004454](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6401004454)、[6401084919](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6401084919)、[6404945456](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6404945456)、[6405490001](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6405490001)、[6405759167](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6405759167)、[6406077095](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/26#issuecomment-6406077095)。
- **OBSERVED：** Homework 2 後續契約位置：[Issue #22](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/22)、[Issue #23](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/23)。它們保持 OPEN；本回顧不修改其內容。
- **OBSERVED：** 主要本地證據包括 `M1-design-handoff-implementer-v3.md`、`M1-qa-review-independent-v3-20261026.md`、`M2-recovery-process-outcome-v1.md`、`M2-watchdog-design-handoff-implementer-v1.md`、`M2-watchdog-design-qa-review-v1.md`、`M2-watchdog-launchd-addendum-handoff-implementer-v1.md`、`M2-watchdog-launchd-addendum-qa-review-v1.md`、`M2-architecture-poc-implementer-handoff-v1.md`、`M2-architecture-poc-qa-prereview-v1.md`、`M2-architecture-poc-design-repair-handoff-v2.md`、`M2-architecture-poc-qa-rereview-v2.md`。完整私有證據、ACK、Logs、PoC fixtures 及逐檔 SHA-256 保存在主 Checkout ignored `local/`，由 closeout manifest 索引；它們不納入本 PR。
- **UNKNOWN：** 本文件不證明 macOS launchd 的實際執行結果、完整程序後代清理、核心 RAM 硬上限、任何實驗輸出或新的 Single-Worker 工作已開始。沒有在本次結案／回顧任務中執行 tests 或模型。
