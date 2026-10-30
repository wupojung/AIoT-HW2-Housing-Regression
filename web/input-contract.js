(function attachRegScopeInputContract(root) {
  "use strict";

  const SHA256 = /^[a-f0-9]{64}$/;
  const CONTROLS = new Set(["number", "text", "select"]);

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
    if (!globalThis.crypto?.subtle) {
      return { valid: false, errors: ["Web Crypto is unavailable; input schema cannot be verified."] };
    }
    try {
      const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
      const actualSha256 = [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
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
    validateLocalPredictionResponse
  });
})(globalThis);
