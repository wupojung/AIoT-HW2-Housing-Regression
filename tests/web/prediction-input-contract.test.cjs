const { test } = require("node:test");
const assert = require("node:assert/strict");
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
