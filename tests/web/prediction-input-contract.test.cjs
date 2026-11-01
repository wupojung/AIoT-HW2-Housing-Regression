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
