# Phase 2 — Data Understanding

**Current detailed spec, docs-only.** Only reviewed public FIG-01/02/03/06; no local-only publication.

### C. Phase 2 — Data Understanding / 靜態 EDA 選取器

**Goal:** explain *already-produced* dataset-specific descriptive research. Phase 2 is NOT an on-demand EDA engine, frontend statistical calculator or interactive Kaggle reanalysis. One selected **published, reviewed** image and its associated prose are shown at a time. Number of analysis buttons is dynamic, from approved case manifest. The four **currently public/reviewed** Ames figures are FIG-01 (overview), FIG-02 (missingness), FIG-03 (target distribution), FIG-06 (numeric correlations); other local figure candidates DO NOT become published buttons just because they exist on disk.

~~~text
+--------------------------------------------------------------------------------------------------+
| PHASE 02 / DATA UNDERSTANDING                                                                    |
| 資料理解：我們從已完成的 EDA 看到了什麼？                                                        |
|                                                                                                  |
| AVAILABLE EDA ANALYSES — dynamic navigation, only approved and published items                   |
| [Dataset Overview*] [Missingness] [SalePrice Distribution] [Numeric Correlations]               |
| [more approved titles wrap onto next row ONLY if the case manifest contains them]               |
|                                                                                                  |
| +----------------------------------------------------------------------------------------------+ |
| | SELECTED: Dataset Overview               [VERIFIED]                                        | |
| |                                                                                              | |
| |                    +---------------------------------------------------+                     | |
| |                    |                                                   |                     | |
| |                    |               FIGURE: SVG / PNG                  |                     | |
| |                    |         one analysis, one principal image        |                     | |
| |                    |                                                   |                     | |
| |                    +---------------------------------------------------+                     | |
| | Alt text / accessible data table for the selected figure                                   | |
| | [Open figure/source]                                                                         | |
| +----------------------------------------------------------------------------------------------+ |
| | DESCRIPTION — what was measured, which population and denominator?                          | |
| | KEY FINDING — what was actually observed, with evidence?                                   | |
| | LIMITATIONS — what cannot be concluded from this descriptive graphic?                       | |
| | DOWNSTREAM IMPLICATION / HYPOTHESIS (if evidence available; NOT automatic adopted policy)    | |
| +----------------------------------------------------------------------------------------------+ |
| [< Previous Phase: Business Understanding]                          [Next Phase: Data Preparation >]|
+--------------------------------------------------------------------------------------------------+
~~~

**Every dynamic EDA selector button**
- **Label:** analysis \`title\` from JSON, not hard-coded first four/eight. Order follows approved manifest array.
- **Click:** set only this button active and **atomically** swap image, alt/accessible data, title, Description, Finding, Limitations, population, source URL, and optional downstream implication; never leave stale captions from previous selection.
- **Default:** first approved/published manifest item for this case; if list empty, show EMPTY/UNAVAILABLE and no inert fake buttons.
- **Hover/focus/keyboard:** visible active and focus indicators; Enter/Space selects. Long lists wrap within selector area on desktop; avoid truncating distinct labels; zero-item empty state.
- **Image:** prebuilt static public SVG/PNG generated offline by Python, with \`object-fit: contain\` behavior (preserve aspect ratio, never crop axes/legend); image failure shows UNAVAILABLE and source, not a dummy empirical figure. Alternative data/description needed for accessibility. No raw private rows on website.
- **Explanatory text:** description, finding and limitations derive from same analysis object. \`next_impact\` is OPTIONAL and must state **candidate/hypothesis** unless an explicitly accepted downstream decision and source exists; absence hides the section, not invented content.
- **Dataset change:** clear previous selection, select first eligible new-case analysis, render unavailable if none. Do not display Ames images in a Used Car case.
- **Evidence:** static images and notes may be served by separately validated public assets. Exact image asset paths and publish permissions must be validated rather than guessed. The deeper Phase 2 empirical details and original FIG evidence table above remain authoritative.

**Minimal manifest item** (all fields sourced from evidence, not code-generated claims):
~~~json
{
  "phase2": {
    "analyses": [
      {
        "id": "missingness",
        "title": "缺失值分析",
        "image": "figures/fig02_missingness_overview.svg",
        "description": "分析各欄位缺失比例與缺失原因。",
        "finding": "部分 NA 代表設施不存在，不能直接視為資料遺漏。",
        "limitations": "缺失值分析本身不代表已完成插補處理。"
      }
    ]
  }
}
~~~
The image path in this snippet is a **schema/path example, not a verified deployable URL**. Optional implementation fields: \`status\`, \`source_url\`, \`source_version\`, \`population\`, \`denominator\`, \`alt_text\`, \`accessible_table_ref\`, \`next_impact\`; do not create an incompatible second protocol when mapping to the earlier Phase 2 finding contract.