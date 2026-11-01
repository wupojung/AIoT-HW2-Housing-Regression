(function attachRegScopeInputContract(root) {
  "use strict";

  const SHA256 = /^[a-f0-9]{64}$/;
  const CONTROLS = new Set(["number", "text", "select"]);

  function sha256HexFallback(input) {
    let bytes;
    if (input instanceof ArrayBuffer) bytes = new Uint8Array(input);
    else if (ArrayBuffer.isView(input)) bytes = new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
    else throw new TypeError("SHA-256 input must be bytes.");

    const length = bytes.length;
    const bitLength = length * 8;
    const paddedLength = Math.ceil((length + 9) / 64) * 64;
    const padded = new Uint8Array(paddedLength);
    padded.set(bytes);
    padded[length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false);
    view.setUint32(paddedLength - 4, bitLength >>> 0, false);
    const k = new Uint32Array([
      0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    ]);
    const state = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
    const words = new Uint32Array(64);
    const rotr = (value, count) => (value >>> count) | (value << (32 - count));
    for (let offset = 0; offset < paddedLength; offset += 64) {
      for (let i = 0; i < 16; i += 1) words[i] = view.getUint32(offset + i * 4, false);
      for (let i = 16; i < 64; i += 1) {
        const x = words[i - 15], y = words[i - 2];
        const s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3);
        const s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10);
        words[i] = (words[i - 16] + s0 + words[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let i = 0; i < 64; i += 1) {
        const sum1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const choice = (e & f) ^ (~e & g);
        const t1 = (h + sum1 + choice + k[i] + words[i]) >>> 0;
        const sum0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const t2 = (sum0 + majority) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0;
        d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      state[0] = (state[0] + a) >>> 0; state[1] = (state[1] + b) >>> 0;
      state[2] = (state[2] + c) >>> 0; state[3] = (state[3] + d) >>> 0;
      state[4] = (state[4] + e) >>> 0; state[5] = (state[5] + f) >>> 0;
      state[6] = (state[6] + g) >>> 0; state[7] = (state[7] + h) >>> 0;
    }
    return [...state].map((word) => word.toString(16).padStart(8, "0")).join("");
  }

  async function sha256Hex(input) {
    if (root.crypto?.subtle) {
      try {
        const digest = await root.crypto.subtle.digest("SHA-256", input);
        return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
      } catch (_error) {
        // Some insecure HTTP origins do not expose Web Crypto.
      }
    }
    return sha256HexFallback(input);
  }

  // This guards the fields used to render UI; the package producer remains responsible
  // for validating the complete document against the published JSON Schema.
  function validate(contract, expected = {}) {
    const errors = [];
    const fail = (message) => errors.push(message);
    if (!contract || typeof contract !== "object" || Array.isArray(contract)) {
      return { valid: false, errors: ["Input contract must be an object."] };
    }
    if (contract.schema_version !== "0.1.0") fail("Unsupported input contract version.");
    if (contract.status !== "VERIFIED" && contract.status !== "PARTIAL") fail("Input contract is not a usable evidence status.");
    if (!contract.case_id || (expected.caseId && contract.case_id !== expected.caseId)) fail("Input contract Case ID mismatch.");
    if (!contract.model_id || (expected.modelId && contract.model_id !== expected.modelId)) fail("Input contract Model ID mismatch.");
    if (expected.modelVersion && contract.model_version !== expected.modelVersion) fail("Input contract Model version mismatch.");
    if (!SHA256.test(contract.model_sha256 || "")) fail("Input contract model digest is invalid.");
    if (contract.api_readiness !== "BLOCKED_NOT_AN_API_ALLOWLIST_OR_ENDPOINT") fail("Input contract API readiness must remain blocked.");
    if (contract.category_values_publication_review !== "REQUIRED_BEFORE_PUBLICATION") fail("Category publication review state is missing.");

    const evidence = contract.source_evidence || {};
    if (expected.runId && evidence.run_id !== expected.runId) fail("Input contract Run ID mismatch.");
    if (expected.configurationId && evidence.configuration_id !== expected.configurationId) fail("Input contract Configuration ID mismatch.");
    if (!Array.isArray(contract.input_features) || contract.input_feature_count !== contract.input_features.length || !contract.input_features.length) {
      fail("Input feature count does not match the contract fields.");
    } else {
      const names = new Set();
      for (const field of contract.input_features) {
        if (!field || typeof field.name !== "string" || !field.name.trim() || names.has(field.name)) {
          fail("Input field names must be non-empty and unique.");
          continue;
        }
        names.add(field.name);
        const options = Array.isArray(field.options) ? field.options : [];
        if (!["number", "category"].includes(field.data_type)) fail(`Unsupported data type for ${field.name}.`);
        if (typeof field.required !== "boolean" || ![true, false, null].includes(field.nullable)) fail(`Required/nullability metadata is invalid for ${field.name}.`);
        if (!CONTROLS.has(field.control_type)) fail(`Unsupported control type for ${field.name}.`);
        if (!Array.isArray(field.options)) fail(`Options must be an array for ${field.name}.`);
        if (field.data_type === "number" && (field.control_type !== "number" || options.length)) fail(`Numeric field metadata is inconsistent for ${field.name}.`);
        if (field.data_type === "category" && !["text", "select"].includes(field.control_type)) fail(`Category field control is inconsistent for ${field.name}.`);
        if (field.control_type === "select" && !options.length) fail(`Select field has no evidenced options: ${field.name}.`);
        if (field.control_type === "select") {
          const optionKeys = options.map((option) => JSON.stringify(option?.value));
          const renderedValues = options.map((option) => option?.value === null ? "" : String(option?.value));
          if (new Set(optionKeys).size !== optionKeys.length
              || new Set(renderedValues).size !== renderedValues.length
              || options.some((option) => !option || !Object.hasOwn(option, "value")
                || !["string", "number", "boolean"].includes(typeof option.value) && option.value !== null
                || (typeof option.value === "number" && !Number.isFinite(option.value))
                || option.source !== "FITTED_ENCODER_CATEGORY" || option.evidence_status !== "VERIFIED" || option.api_allowlisted !== false)) {
            fail(`Select options are not unique primitive values with verified provenance for ${field.name}.`);
          }
        }
        if (field.minimum !== null && (typeof field.minimum !== "number" || !Number.isFinite(field.minimum))) fail(`Minimum is invalid for ${field.name}.`);
        if (field.maximum !== null && (typeof field.maximum !== "number" || !Number.isFinite(field.maximum))) fail(`Maximum is invalid for ${field.name}.`);
        if (field.minimum !== null && field.maximum !== null && field.minimum > field.maximum) fail(`Range is reversed for ${field.name}.`);
      }
      const rawOrder = contract.preprocessing_reference?.raw_input_order;
      if (!Array.isArray(rawOrder) || rawOrder.length !== contract.input_features.length
          || contract.input_features.some((field) => !field || typeof field.name !== "string")
          || rawOrder.some((name, index) => name !== contract.input_features[index].name)) {
        fail("Preprocessing raw input order does not match the contract fields.");
      }
    }
    return { valid: errors.length === 0, errors };
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  async function verifySchemaBytes(bytes, claimedSha256, expectedSha256) {
    if (!(bytes instanceof ArrayBuffer) && !ArrayBuffer.isView(bytes)) {
      return { valid: false, errors: ["Input schema response must be raw bytes."] };
    }
    if (!SHA256.test(claimedSha256 || "") || !SHA256.test(expectedSha256 || "")) {
      return { valid: false, errors: ["Input schema digest is invalid."] };
    }
    try {
      const actualSha256 = await sha256Hex(bytes);
      if (actualSha256 !== claimedSha256 || actualSha256 !== expectedSha256) {
        return { valid: false, errors: ["Input schema SHA-256 does not match the pinned digest."] };
      }
      const schema = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
      return { valid: true, errors: [], schema };
    } catch (_error) {
      return { valid: false, errors: ["Input schema bytes are not valid UTF-8 JSON."] };
    }
  }

  function validateLocalPredictionResponse(payload, expected = {}) {
    const valid = payload && Number.isFinite(payload.prediction)
      && payload.case_id === expected.caseId
      && payload.model_id === expected.modelId
      && payload.model_version === expected.modelVersion
      && payload.run_id === expected.runId
      && payload.configuration_id === expected.configurationId;
    return { valid: Boolean(valid) };
  }

  function resolveVerifiedTargetUnit(caseDocument, prediction, expectedCaseId) {
    if (!caseDocument || !prediction || typeof expectedCaseId !== "string" || !expectedCaseId
        || caseDocument.case_id !== expectedCaseId || prediction.case_id !== expectedCaseId
        || typeof prediction.target !== "string" || caseDocument.target?.raw_field_id !== prediction.target) return null;
    const unit = caseDocument.target.unit;
    return typeof unit === "string" && unit.trim() ? unit.trim() : null;
  }

  function addVerifiedCasePackageTargetUnit(columns, rows, caseDocument, batch, contract, expected) {
    const evidence = contract?.source_evidence;
    const target = caseDocument?.target;
    if (!Array.isArray(columns) || !Array.isArray(rows) || !caseDocument || !batch || !contract || !expected
        || caseDocument.case_id !== expected.caseId || batch.case_id !== expected.caseId
        || batch.model_id !== expected.modelId || contract.model_id !== expected.modelId
        || batch.model_version !== expected.modelVersion || contract.model_version !== expected.modelVersion
        || batch.run_id !== expected.runId || evidence?.run_id !== expected.runId
        || batch.configuration_id !== expected.configurationId || evidence?.configuration_id !== expected.configurationId
        || typeof expected.targetField !== "string" || target?.raw_field_id !== expected.targetField
        || typeof target.unit !== "string" || !target.unit.trim()
        || columns.includes("case_package_target_unit")) return { columns, rows };
    const unit = target.unit.trim();
    return {
      columns: [...columns, "case_package_target_unit"],
      rows: rows.map((row) => ({ ...row, case_package_target_unit: unit }))
    };
  }

  function batchResultsCsv(columns, rows) {
    if (!Array.isArray(columns) || !columns.every((column) => typeof column === "string") || !Array.isArray(rows)) {
      throw new TypeError("Batch result columns and rows are required.");
    }
    const cell = (value) => {
      if (value === null || value === undefined) return "";
      if (typeof value === "number" && Number.isFinite(value)) return Object.is(value, -0) ? "-0" : String(value);
      const text = String(value);
      let firstMeaningful = 0;
      while (firstMeaningful < text.length) {
        const code = text.charCodeAt(firstMeaningful);
        if (text[firstMeaningful].trim() === "" || code < 0x20 || code === 0x7f) firstMeaningful += 1;
        else break;
      }
      const formula = firstMeaningful < text.length && "=+-@".includes(text[firstMeaningful]);
      const safe = formula ? `'${text}` : text;
      return `"${safe.replaceAll('"', '""')}"`;
    };
    const data = rows.map((row) => columns.map((column) => {
      if (Object.hasOwn(row?.input || {}, column)) return row.input[column];
      if (column === "prediction_status") return row?.status;
      return row?.[column];
    }));
    return [columns, ...data].map((record) => record.map(cell).join(",")).join("\r\n") + "\r\n";
  }

  function inspectCsvHeader(text, expectedNames) {
    if (typeof text !== "string" || !Array.isArray(expectedNames)) return { valid: false, error: "CSV 內容或輸入契約不可用。" };
    const source = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
    const headers = [];
    let cell = "";
    let quoted = false;
    let afterQuote = false;
    let ended = false;
    for (let index = 0; index < source.length; index += 1) {
      const character = source[index];
      if (quoted) {
        if (character === '"' && source[index + 1] === '"') { cell += '"'; index += 1; }
        else if (character === '"') { quoted = false; afterQuote = true; }
        else cell += character;
        continue;
      }
      if (afterQuote && character !== "," && character !== "\r" && character !== "\n") {
        return { valid: false, error: "CSV 標題列的引號格式錯誤。" };
      }
      if (character === '"') {
        if (cell !== "" || afterQuote) return { valid: false, error: "CSV 標題列的引號格式錯誤。" };
        quoted = true;
      } else if (character === ",") {
        headers.push(cell); cell = ""; afterQuote = false;
      } else if (character === "\r" || character === "\n") {
        headers.push(cell); ended = true;
        if (character === "\r" && source[index + 1] === "\n") index += 1;
        break;
      } else {
        cell += character;
      }
    }
    if (quoted) return { valid: false, error: "CSV 標題列缺少結尾引號。" };
    if (!ended) headers.push(cell);
    if (!headers.length || headers.every((header) => header === "")) return { valid: false, error: "CSV 缺少標題列。" };
    if (new Set(headers).size !== headers.length) return { valid: false, headers, error: "CSV 標題列有重複欄位。" };
    const missing = expectedNames.filter((name) => !headers.includes(name));
    const extra = headers.filter((name) => !expectedNames.includes(name));
    return { valid: missing.length === 0 && extra.length === 0, headers, missing, extra,
      error: missing.length || extra.length ? "CSV 欄位與目前模型輸入契約不一致。" : null };
  }

  function validateLocalBatchPredictionResponse(payload, expected = {}) {
    const resultColumns = ["row_number", "prediction", "prediction_unit", "prediction_status", "warning_code", "error_code", "error_message"];
    const expectedColumns = Array.isArray(expected.inputNames) ? [...expected.inputNames, ...resultColumns] : null;
    if (!payload || payload.case_id !== expected.caseId || payload.model_id !== expected.modelId
        || payload.model_version !== expected.modelVersion || payload.run_id !== expected.runId
        || payload.configuration_id !== expected.configurationId || payload.schema_sha256 !== expected.schemaSha256
        || !Array.isArray(payload.rows) || !Array.isArray(payload.columns)
        || !expectedColumns || payload.columns.length !== expectedColumns.length
        || payload.columns.some((column, index) => column !== expectedColumns[index])
        || payload.total_rows !== payload.rows.length
        || payload.valid_rows + payload.error_rows !== payload.total_rows
        || !Number.isInteger(payload.total_rows) || payload.total_rows < 1 || payload.total_rows > 100) {
      return { valid: false };
    }
    const validRows = payload.rows.filter((row) => row && row.status === "SUCCESS");
    const errorRows = payload.rows.filter((row) => row && row.status === "ERROR");
    let previousSourceLine = 1;
    const rowsWellFormed = payload.rows.every((row) => {
      if (!row || typeof row !== "object" || Array.isArray(row)) return false;
      const validLine = Number.isInteger(row.row_number) && row.row_number > previousSourceLine;
      previousSourceLine = row.row_number;
      const warningMatchesValue = row.warning_code === "negative_prediction"
        ? Number.isFinite(row.prediction) && row.prediction < 0
        : row.warning_code === null && row.status === "SUCCESS" && row.prediction >= 0;
      return validLine && (
        row.status === "SUCCESS" && Number.isFinite(row.prediction) && warningMatchesValue
        || row.status === "ERROR" && row.prediction === null && row.warning_code === null
          && typeof row.error_code === "string" && typeof row.error_message === "string"
      );
    });
    return { valid: rowsWellFormed && validRows.length === payload.valid_rows && errorRows.length === payload.error_rows };
  }

  function validateCarNumericDomain(name, value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "請輸入有限的數值。";
    if (name === "year" && value <= 0) return "year 必須大於 0；目前未設定上限。";
    if (name === "odometer" && value < 0) return "odometer 不可為負數；單位與合理範圍未確認。";
    if (name === "image_count" && value < 0) return "image_count 不可為負數；0 可接受。";
    return null;
  }

  function renderFields(contract, renderOptions = {}) {
    if (!validate(contract).valid) throw new Error("Cannot render an invalid Prediction Input Schema.");
    const controls = contract.input_features.map((field, index) => {
      const id = `p6-contract-field-${index}`;
      const ui = renderOptions.fieldUi?.[field.name] || {};
      const displayName = ui.title || field.name;
      const description = ui.description || "欄位中文語意待來源確認。";
      const evidence = ui.evidence === "PROPOSED" ? "建議翻譯" : "語意待確認";
      const required = field.required && field.nullable !== true ? "required" : "";
      const nullable = field.nullable === true
        ? "契約允許 null"
        : field.nullable === false
          ? "契約不允許 null"
          : "契約未確認是否可為 null";
      const requirement = field.required === true ? "必填" : field.required === false ? "選填" : "必填狀態未知";
      const runtimePolicy = renderOptions.runtimePolicy
        ? [
          renderOptions.runtimePolicy.requiresCompleteFieldSet === true ? "此 API 要求完整欄位" : null,
          renderOptions.runtimePolicy.acceptsNull === false ? "此 API 拒絕 null" : renderOptions.runtimePolicy.acceptsNull === true ? "此 API 接受 null" : null
        ].filter(Boolean).join("；")
        : "";
      const limits = field.data_type === "number"
        ? `${field.unit ? `單位：${escapeHTML(field.unit)}` : "單位未確認"} · ${field.minimum !== null || field.maximum !== null ? `契約範圍 ${field.minimum ?? "−∞"}–${field.maximum ?? "+∞"}` : "契約未提供輸入上下限；觀測範圍未知"}`
        : field.data_type === "category"
          ? `選項來源：${Array.isArray(field.options) && field.options.length ? "已擬合 Encoder 類別；非公開 API allowlist" : "未知"}`
          : "輸入語意待確認";
      let control;
      if (field.control_type === "select") {
        const currentValue = renderOptions.values?.[field.name];
        let placeholderValue = "__REGSCOPE_SELECT__";
        while (field.options.some((option) => String(option.value) === placeholderValue)) placeholderValue += "_";
        const options = field.options.map((option) => {
          const value = option.value === null ? "" : String(option.value);
          const selected = currentValue !== undefined && String(currentValue) === value ? "selected" : "";
          return `<option value="${escapeHTML(value)}" ${selected}>${escapeHTML(value)}</option>`;
        }).join("");
        const emptyChoice = renderOptions.emptySelect && (currentValue === undefined || currentValue === placeholderValue)
          ? `<option value="${escapeHTML(placeholderValue)}" data-contract-placeholder="true" selected disabled>請選擇類別</option>`
          : field.nullable === true && !field.options.some((option) => option.value === null || String(option.value) === "")
            ? '<option value="">—</option>' : "";
        control = `<select id="${id}" name="${escapeHTML(field.name)}" ${required} aria-label="${escapeHTML(field.name)}">${emptyChoice}${options}</select>`;
      } else {
        const min = field.minimum === null ? "" : `min="${field.minimum}"`;
        const max = field.maximum === null ? "" : `max="${field.maximum}"`;
        const value = renderOptions.values?.[field.name];
        control = `<input id="${id}" name="${escapeHTML(field.name)}" type="${field.control_type === "number" ? "number" : "text"}" value="${value === undefined ? "" : escapeHTML(value)}" ${required} ${min} ${max} aria-label="${escapeHTML(field.name)}">`;
      }
      return `<article class="p6-feature-card" data-contract-field="${escapeHTML(field.name)}"><label class="p6-field-label" for="${id}"><strong>${escapeHTML(displayName)}${displayName === field.name ? "" : ` · ${escapeHTML(field.name)}`}</strong><span>${escapeHTML(field.data_type)} · 契約：${requirement} · ${nullable}${runtimePolicy ? ` · ${escapeHTML(runtimePolicy)}` : ""} · ${evidence}</span><span>${escapeHTML(description)}</span><span>${limits}</span></label>${control}</article>`;
    }).join("");
    return `<div class="p6-feature-grid">${controls}</div>`;
  }

  root.RegScopeInputContract = Object.freeze({
    validateForUI: validate,
    renderFields,
    verifySchemaBytes,
    sha256Hex,
    sha256HexFallback,
    validateLocalPredictionResponse,
    validateCarNumericDomain,
    resolveVerifiedTargetUnit,
    addVerifiedCasePackageTargetUnit,
    batchResultsCsv,
    inspectCsvHeader,
    validateLocalBatchPredictionResponse
  });
})(globalThis);
