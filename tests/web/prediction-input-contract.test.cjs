const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
require("../../web/input-contract.js");

const sha = "a".repeat(64);
function syntheticContract(count) {
  const input_features = Array.from({ length: count }, (_, index) => ({
    name: `demo_field_${index + 1}`,
    data_type: index === 1 ? "category" : "number",
    required: true,
    nullable: false,
    control_type: index === 1 ? "select" : "number",
    options: index === 1 ? [
      { value: "SYNTHETIC_Value A", source: "FITTED_ENCODER_CATEGORY", evidence_status: "VERIFIED", infrequent: false, api_allowlisted: false }
    ] : [],
    minimum: null,
    maximum: null
  }));
  return {
    schema_version: "0.1.0", case_id: "synthetic-case", model_id: "synthetic-model", model_version: "1",
    model_sha256: sha, status: "PARTIAL", api_readiness: "BLOCKED_NOT_AN_API_ALLOWLIST_OR_ENDPOINT",
    category_values_publication_review: "REQUIRED_BEFORE_PUBLICATION",
    input_feature_count: count, input_features,
    preprocessing_reference: { raw_input_order: input_features.map((field) => field.name) },
    source_evidence: { run_id: "run-1", configuration_id: "config-1" }
  };
}

test("accepts both small and larger contract field sets without fixed counts", () => {
  for (const count of [5, 15]) {
    const contract = syntheticContract(count);
    const result = globalThis.RegScopeInputContract.validateForUI(contract, {
      caseId: "synthetic-case", modelId: "synthetic-model", modelVersion: "1", runId: "run-1", configurationId: "config-1"
    });
    assert.deepEqual(result, { valid: true, errors: [] });
    assert.equal((globalThis.RegScopeInputContract.renderFields(contract).match(/class="p6-feature-card"/g) || []).length, count);
  }
});

test("keeps fitted category values as exact source values", () => {
  const contract = syntheticContract(2);
  const result = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.equal(result.valid, true);
  assert.equal(contract.input_features[1].options[0].value, "SYNTHETIC_Value A");
});

test("rejects identity mismatch, invalid count, unsupported status and unreviewed category metadata", () => {
  const contract = syntheticContract(2);
  const identity = globalThis.RegScopeInputContract.validateForUI(contract, { caseId: "another-case" });
  assert.equal(identity.valid, false);
  assert.ok(identity.errors.some((error) => error.includes("Case ID mismatch")));

  contract.input_feature_count = 3;
  contract.status = "MOCK";
  contract.input_features[1].options[0].api_allowlisted = true;
  const invalid = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.equal(invalid.valid, false);
  assert.ok(invalid.errors.some((error) => error.includes("feature count")));
  assert.ok(invalid.errors.some((error) => error.includes("evidence status")));

  contract.input_feature_count = 2;
  const category = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.ok(category.errors.some((error) => error.includes("verified provenance")));
});

test("rejects category-number controls and duplicate options", () => {
  const contract = syntheticContract(2);
  contract.input_features[1].control_type = "number";
  contract.input_features[1].options = [];
  const mismatch = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.ok(mismatch.errors.some((error) => error.includes("Category field control")));

  contract.input_features[1].control_type = "select";
  contract.input_features[1].options = [
    { value: "same", source: "FITTED_ENCODER_CATEGORY", evidence_status: "VERIFIED", infrequent: false, api_allowlisted: false },
    { value: "same", source: "FITTED_ENCODER_CATEGORY", evidence_status: "VERIFIED", infrequent: false, api_allowlisted: false }
  ];
  const duplicates = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.ok(duplicates.errors.some((error) => error.includes("unique primitive values")));

  contract.input_features[1].options = [
    { value: 1, source: "FITTED_ENCODER_CATEGORY", evidence_status: "VERIFIED", infrequent: false, api_allowlisted: false },
    { value: "1", source: "FITTED_ENCODER_CATEGORY", evidence_status: "VERIFIED", infrequent: false, api_allowlisted: false }
  ];
  const renderedCollision = globalThis.RegScopeInputContract.validateForUI(contract);
  assert.ok(renderedCollision.errors.some((error) => error.includes("unique primitive values")));
});

test("malformed input fails closed without throwing", () => {
  const result = globalThis.RegScopeInputContract.validateForUI({
    ...syntheticContract(1), input_features: [{ name: "x" }], input_feature_count: 1,
    preprocessing_reference: { raw_input_order: ["x"] }
  });
  assert.equal(result.valid, false);
  assert.ok(result.errors.length > 0);
  assert.throws(() => globalThis.RegScopeInputContract.renderFields(result), /invalid Prediction Input Schema/);
});

test("escapes field names and preserves category values in rendered controls", () => {
  const contract = syntheticContract(2);
  contract.input_features[0].name = 'demo_<field>"';
  contract.preprocessing_reference.raw_input_order[0] = 'demo_<field>"';
  contract.input_features[1].options[0].value = "SYNTHETIC <A&B>";
  const html = globalThis.RegScopeInputContract.renderFields(contract);
  assert.match(html, /demo_&lt;field&gt;&quot;/);
  assert.match(html, /SYNTHETIC &lt;A&amp;B&gt;/);
  assert.doesNotMatch(html, /<field>/);
});

test("local inference form starts unselected and can safely restore entered values", () => {
  const contract = syntheticContract(2);
  const initial = globalThis.RegScopeInputContract.renderFields(contract, { emptySelect: true });
  assert.match(initial, /data-contract-placeholder="true" selected disabled>請選擇類別<\/option>/);
  assert.match(initial, /name="demo_field_1" type="number" value=""/);

  const restored = globalThis.RegScopeInputContract.renderFields(contract, {
    emptySelect: true,
    values: { demo_field_1: "1200.5", demo_field_2: "SYNTHETIC_Value A" }
  });
  assert.match(restored, /value="1200\.5"/);
  assert.match(restored, /<option value="SYNTHETIC_Value A" selected>/);
});

test("display labels are escaped metadata and leave raw contract names intact", () => {
  const contract = syntheticContract(2);
  const html = globalThis.RegScopeInputContract.renderFields(contract, {
    fieldUi: {
      demo_field_1: { title: "<車輛欄位>", description: "待確認 & 暫譯", evidence: "PROPOSED" }
    }
  });
  assert.match(html, /&lt;車輛欄位&gt; · demo_field_1/);
  assert.match(html, /待確認 &amp; 暫譯/);
  assert.match(html, /data-contract-field="demo_field_1"/);
  assert.match(html, /name="demo_field_1"/);
  assert.match(html, /單位未確認/);
});

test("unknown contract nullability stays distinct from verified API null behavior", () => {
  const contract = syntheticContract(2);
  contract.input_features[0].nullable = null;
  const contractOnly = globalThis.RegScopeInputContract.renderFields(contract);
  assert.match(contractOnly, /契約未確認是否可為 null/);
  assert.doesNotMatch(contractOnly, /此 API 拒絕 null/);

  const withRuntime = globalThis.RegScopeInputContract.renderFields(contract, {
    runtimePolicy: { requiresCompleteFieldSet: true, acceptsNull: false }
  });
  assert.match(withRuntime, /契約：必填 · 契約未確認是否可為 null · 此 API 要求完整欄位；此 API 拒絕 null/);
});

test("verifies raw schema bytes against both API and pinned SHA-256", async () => {
  const contract = syntheticContract(2);
  const bytes = new TextEncoder().encode(JSON.stringify(contract));
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
    .map((value) => value.toString(16).padStart(2, "0")).join("");
  const accepted = await globalThis.RegScopeInputContract.verifySchemaBytes(bytes, digest, digest);
  assert.equal(accepted.valid, true);
  assert.deepEqual(accepted.schema, contract);

  const altered = new TextEncoder().encode(JSON.stringify({ ...contract, model_id: "attacker-model" }));
  const rejected = await globalThis.RegScopeInputContract.verifySchemaBytes(altered, digest, digest);
  assert.equal(rejected.valid, false);
  assert.match(rejected.errors[0], /SHA-256/);
});

test("SHA-256 stays available without Web Crypto on direct HTTP origins", async () => {
  const helper = globalThis.RegScopeInputContract;
  const known = new TextEncoder().encode("abc");
  assert.equal(await helper.sha256HexFallback(known), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

  const longer = new Uint8Array(4097).map((_, index) => index % 251);
  assert.equal(await helper.sha256HexFallback(longer), createHash("sha256").update(longer).digest("hex"));

  const originalCryptoDescriptor = Object.getOwnPropertyDescriptor(globalThis, "crypto");
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: undefined });
  try {
    assert.equal(await helper.sha256Hex(known), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    const contract = syntheticContract(2);
    const bytes = new TextEncoder().encode(JSON.stringify(contract));
    const digest = await helper.sha256Hex(bytes);
    const result = await helper.verifySchemaBytes(bytes, digest, digest);
    assert.equal(result.valid, true);
  } finally {
    Object.defineProperty(globalThis, "crypto", originalCryptoDescriptor);
  }
});

test("requires prediction response to match the pinned model version and run", () => {
  const expected = { caseId: "car", modelId: "model", modelVersion: "v1", runId: "run", configurationId: "config" };
  const payload = {
    prediction: 1.25, case_id: "car", model_id: "model", model_version: "v1", run_id: "run", configuration_id: "config"
  };
  assert.deepEqual(globalThis.RegScopeInputContract.validateLocalPredictionResponse(payload, expected), { valid: true });
  assert.equal(globalThis.RegScopeInputContract.validateLocalPredictionResponse({ ...payload, model_version: "v2" }, expected).valid, false);
  assert.equal(globalThis.RegScopeInputContract.validateLocalPredictionResponse({ ...payload, prediction: Infinity }, expected).valid, false);
});

test("CAR numeric pre-submit checks match API domain floors without inventing upper limits", () => {
  const validate = globalThis.RegScopeInputContract.validateCarNumericDomain;
  assert.equal(validate("year", 0), "year 必須大於 0；目前未設定上限。");
  assert.equal(validate("year", -1), "year 必須大於 0；目前未設定上限。");
  assert.equal(validate("year", 2018), null);
  assert.equal(validate("odometer", -0.1), "odometer 不可為負數；單位與合理範圍未確認。");
  assert.equal(validate("odometer", 0), null);
  assert.equal(validate("image_count", -1), "image_count 不可為負數；0 可接受。");
  assert.equal(validate("image_count", 0), null);
  assert.equal(validate("feature_count", -1), null);
});

test("renders CAR plausibility rules separately from schema and observed ranges", () => {
  const contract = syntheticContract(3);
  const fields = ["year", "odometer", "image_count"];
  contract.input_features.forEach((field, index) => {
    field.name = fields[index];
    field.data_type = "number";
    field.control_type = "number";
    field.options = [];
  });
  contract.preprocessing_reference.raw_input_order = fields;
  const html = globalThis.RegScopeInputContract.renderFields(contract, {
    fieldUi: {
      year: { title: "車輛年份", description: "API 合理性檢查：年份須大於 0，未設定上限；這不是契約或觀測範圍。", evidence: "PROPOSED" },
      odometer: { title: "里程數", description: "API 合理性檢查：不可為負數；這不是契約界限。距離單位、上限及觀測範圍均未知。", evidence: "PROPOSED" },
      image_count: { title: "圖片數量", description: "API 合理性檢查：不可為負數，0 可接受；這不是契約或觀測範圍。", evidence: "PROPOSED" }
    }
  });
  assert.match(html, /API 合理性檢查：年份須大於 0，未設定上限；這不是契約或觀測範圍。/);
  assert.match(html, /API 合理性檢查：不可為負數；這不是契約界限。距離單位、上限及觀測範圍均未知。/);
  assert.match(html, /API 合理性檢查：不可為負數，0 可接受；這不是契約或觀測範圍。/);
  assert.match(html, /契約未提供輸入上下限；觀測範圍未知/);
});

test("resolves a displayed unit only from a matching verified case target", () => {
  const resolve = globalThis.RegScopeInputContract.resolveVerifiedTargetUnit;
  const caseDocument = { case_id: "car", target: { raw_field_id: "price", unit: "USD" } };
  const prediction = { case_id: "car", target: "price", unit: null };
  assert.equal(resolve(caseDocument, prediction, "car"), "USD");
  assert.equal(resolve(caseDocument, { ...prediction, case_id: "other" }, "car"), null);
  assert.equal(resolve({ ...caseDocument, case_id: "other" }, prediction, "car"), null);
  assert.equal(resolve(caseDocument, { ...prediction, target: "other_target" }, "car"), null);
  assert.equal(resolve({ ...caseDocument, target: { raw_field_id: "price", unit: null } }, prediction, "car"), null);
});

test("checks CSV headers with BOM, quoted commas, reordering and exact field identity", () => {
  const inspect = globalThis.RegScopeInputContract.inspectCsvHeader;
  assert.deepEqual(inspect("\uFEFF\"make\",mileage\r\n", ["mileage", "make"]), {
    valid: true, headers: ["make", "mileage"], missing: [], extra: [], error: null
  });
  assert.equal(inspect("mileage,make,make\n", ["mileage", "make"]).error, "CSV 標題列有重複欄位。");
  assert.deepEqual(inspect("mileage,unexpected\n", ["mileage", "make"]).extra, ["unexpected"]);
  assert.equal(inspect('mileage,"unterminated', ["mileage"]).valid, false);
});

test("batch response identity is pinned and CSV export escapes spreadsheet formulas", () => {
  const helper = globalThis.RegScopeInputContract;
  const expected = { caseId: "car", modelId: "model", modelVersion: "v1", runId: "run", configurationId: "cfg", schemaSha256: sha, inputNames: ["trim"] };
  const response = {
    case_id: "car", model_id: "model", model_version: "v1", run_id: "run", configuration_id: "cfg", schema_sha256: sha,
    columns: ["trim", "row_number", "prediction", "prediction_unit", "prediction_status", "warning_code", "error_code", "error_message"], total_rows: 1, valid_rows: 1, error_rows: 0,
    rows: [{ row_number: 2, input: { trim: "\t=1+1" }, prediction: -2, status: "SUCCESS", warning_code: "negative_prediction", error_code: null, error_message: null }]
  };
  assert.deepEqual(helper.validateLocalBatchPredictionResponse(response, expected), { valid: true });
  assert.deepEqual(helper.validateLocalBatchPredictionResponse({ ...response, columns: ["other", ...response.columns.slice(1)] }, expected), { valid: false });
  assert.deepEqual(helper.validateLocalBatchPredictionResponse({ ...response, rows: [{ ...response.rows[0], row_number: 1 }] }, expected), { valid: false });
  assert.deepEqual(helper.validateLocalBatchPredictionResponse({ ...response, rows: [{ ...response.rows[0], warning_code: null }] }, expected), { valid: false });
  assert.deepEqual(helper.validateLocalBatchPredictionResponse({ ...response, rows: [response.rows[0], { row_number: 4, prediction: null, status: "ERROR", warning_code: null, error_code: "invalid_number", error_message: "bad" }], total_rows: 2, valid_rows: 1, error_rows: 1 }, expected), { valid: true });
  assert.deepEqual(helper.validateLocalBatchPredictionResponse({ ...response, rows: [null] }, expected), { valid: false });
  assert.equal(helper.validateLocalBatchPredictionResponse({ ...response, model_version: "other" }, expected).valid, false);
  assert.equal(helper.validateLocalBatchPredictionResponse({ ...response, schema_sha256: "0".repeat(64) }, expected).valid, false);
  const csv = helper.batchResultsCsv(response.columns, response.rows);
  assert.match(csv, /"'\t=1\+1"/);
  assert.match(csv, /,2,-2,,"SUCCESS","negative_prediction"/);
  assert.match(helper.batchResultsCsv(["x"], [{ input: { x: "@SUM(A1:A2)" } }]), /"'@SUM/);
});

test("CSV export preserves finite numbers as numeric cells and nulls as empty cells", () => {
  const csv = globalThis.RegScopeInputContract.batchResultsCsv(
    ["positive", "negative", "negative_zero", "formula", "tab_formula", "null_value", "undefined_value"],
    [{ input: {
      positive: 123.5,
      negative: -45.25,
      negative_zero: -0,
      formula: "=SUM(A1:A2)",
      tab_formula: "\t=1+1",
      null_value: null
    } }]
  );
  assert.equal(csv, '"positive","negative","negative_zero","formula","tab_formula","null_value","undefined_value"\r\n123.5,-45.25,-0,"\'=SUM(A1:A2)","\'\t=1+1",,\r\n');
});

test("case-package target unit is exported only for matching CAR case, target and model identity", () => {
  const helper = globalThis.RegScopeInputContract;
  const expected = { caseId: "car", modelId: "model", modelVersion: "v1", runId: "run", configurationId: "cfg", targetField: "price" };
  const caseDocument = { case_id: "car", target: { raw_field_id: "price", unit: "USD" } };
  const contract = { case_id: "car", model_id: "model", model_version: "v1", source_evidence: { run_id: "run", configuration_id: "cfg" } };
  const batch = { case_id: "car", model_id: "model", model_version: "v1", run_id: "run", configuration_id: "cfg", schema_sha256: sha, columns: ["price", "prediction_unit"], rows: [{ input: { price: 1 }, prediction_unit: null }] };
  const output = helper.addVerifiedCasePackageTargetUnit(batch.columns, batch.rows, caseDocument, batch, contract, expected);
  assert.deepEqual(output.columns, ["price", "prediction_unit", "case_package_target_unit"]);
  assert.equal(output.rows[0].case_package_target_unit, "USD");
  assert.equal(output.rows[0].prediction_unit, null);
  for (const [changedCase, changedBatch, changedContract, changedExpected] of [
    [{ ...caseDocument, case_id: "other" }, batch, contract, expected],
    [caseDocument, { ...batch, case_id: "other" }, contract, expected],
    [caseDocument, { ...batch, model_version: "other" }, contract, expected],
    [caseDocument, { ...batch, model_id: "other" }, contract, expected],
    [caseDocument, { ...batch, run_id: "other" }, contract, expected],
    [caseDocument, { ...batch, configuration_id: "other" }, contract, expected],
    [caseDocument, batch, { ...contract, model_id: "other" }, expected],
    [caseDocument, batch, { ...contract, source_evidence: { run_id: "other", configuration_id: "cfg" } }, expected],
    [{ ...caseDocument, target: { ...caseDocument.target, raw_field_id: "other" } }, batch, contract, expected],
    [{ ...caseDocument, target: { ...caseDocument.target, unit: null } }, batch, contract, expected]
  ]) {
    const unavailable = helper.addVerifiedCasePackageTargetUnit(batch.columns, batch.rows, changedCase, changedBatch, changedContract, changedExpected);
    assert.deepEqual(unavailable, { columns: batch.columns, rows: batch.rows });
  }
  const collision = helper.addVerifiedCasePackageTargetUnit(
    ["case_package_target_unit"], batch.rows, caseDocument, batch, contract, expected
  );
  assert.deepEqual(collision, { columns: ["case_package_target_unit"], rows: batch.rows });
  const enriched = helper.addVerifiedCasePackageTargetUnit(batch.columns, batch.rows, caseDocument, batch, contract, expected);
  const csv = helper.batchResultsCsv(enriched.columns, enriched.rows);
  assert.match(csv, /prediction_unit","case_package_target_unit"\r\n[\s\S]*?,,"USD"\r\n/);
});
