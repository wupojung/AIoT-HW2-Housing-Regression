# ADR-001｜P4-B Recovery：以可重現研究取代過度複雜的執行架構

**狀態：提案，待 Docs PR 獨立 Review 與 Owner Merge 後生效**  
**日期：2026-10-26** · **依據：** [Recovery #28](https://github.com/wupojung/AIoT-HW2-Housing-Regression/issues/28) · **涉及：** #21、#22、#23、#26

## 背景
原 P4-B 協定要求 5 outer ×3 inner Nested CV、Forward SFS，以及跨 Windows/macOS 的受限 Runner。#26 的 macOS Supervisor 設計沒有進入實測；不能聲稱 PASS，也不應再把 production-grade 安全隔離作為課堂研究的必要先決條件。Phase 1–3 和 P4-A 的 5-fold OLS 研究結果保留，不重跑，也不將不同 fold 成績直接比高低。

## 決策
1. 只研究 Pearson、Mutual Information、Lasso、ElasticNet、Ridge RFE；Forward SFS、F-test 單獨方法、Group Lasso 排除於必要交件。
2. 僅在 1,168 筆 Development 上採固定 seed 42 的 3-fold CV，所有資料學習步驟須 fold-local；保留 292 sealed Holdout 到 Phase 5 最終一次評估。
3. 使用同折 all-feature OLS baseline；五方法統一報選特徵後 OLS，Lasso/ElasticNet native predictions 分開報。
4. 本版採 encoded-column 作選取單位，Pearson/MI/Ridge RFE K={2,3,5,10,20}；需揭露 raw↔encoded 對照及自然非零數差異；其他具體參數及安全預檢固定於 P4-B Protocol。
5. 最多四個 Python Workers、人工監控與 run-specific 精準停止；只有控制介面、synthetic 預檢實測 PASS 且 Owner 另授權才能真的執行。不得新增 launchd/Watchdog 等平台依賴。
6. 文件 PR/研究程式/真實實驗/Holdout/Merge/部署分離授權；依據對應工作 Issue 留存證據。

## 取捨與限制
3-fold 非 nested 方法選擇可能使最佳 CV 結果偏樂觀，必須誠實揭露而不能稱 unbiased final test。以 encoded columns 計數會拆分原始類別欄位；One-Hot、標準化與正則化的相對重要性不代表因果。四 Worker 依賴人工值守，20/24 GiB 僅是 soft threshold 並非 OS 硬上限；OS、程式與身份隔離的實測狀態仍是 NOT RUN。

## 生效與遷移
正式合併後由 PM 將 #21、#22、#23 的舊合約標為 SUPERSEDED（保留歷史），新增指向本 ADR 與 [新協定](../crisp-dm/04-modeling-p4b-experiment-protocol.md)。#26／PR #27 屬歷史回顧，不再是研究 Gate。後續若需更換方法、fold 或 Holdout 使用方式須另經 Owner 明確決策。