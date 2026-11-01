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

  function renderFields(contract, renderOptions = {}) {
    if (!validate(contract).valid) throw new Error("Cannot render an invalid Prediction Input Schema.");
    const controls = contract.input_features.map((field, index) => {
      const id = `p6-contract-field-${index}`;
      const required = field.required && field.nullable !== true ? "required" : "";
      const nullable = field.nullable === true ? "可留空" : field.nullable === false ? "不可留空" : "缺值規則未知";
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
      return `<article class="p6-feature-card"><label class="p6-field-label" for="${id}"><strong>${escapeHTML(field.name)}</strong><span>${escapeHTML(field.data_type)} · ${nullable}${field.unit ? ` · ${escapeHTML(field.unit)}` : ""}</span></label>${control}</article>`;
    }).join("");
    return `<div class="p6-feature-grid">${controls}</div>`;
  }

  root.RegScopeInputContract = Object.freeze({
    validateForUI: validate,
    renderFields,
    verifySchemaBytes,
    sha256Hex,
    sha256HexFallback,
    validateLocalPredictionResponse
  });
})(globalThis);
