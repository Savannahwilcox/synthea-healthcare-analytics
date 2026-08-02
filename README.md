# EHR Interoperability & Data Quality Audit

A data-quality and population-health audit of a synthetic EHR population, built on
FHIR R4: the data standard real electronic health record systems use to exchange
patient information. No real patient data is used anywhere in this project.

## Data source

[Synthea](https://github.com/synthetichealth/synthea)'s official pre-generated sample
dataset (555 synthetic patients, FHIR R4 format), published by MITRE at
[synthea-sample-data](https://github.com/synthetichealth/synthea-sample-data). Synthea
is a widely-used open-source tool for generating realistic-but-fake patient populations,
specifically so people can build and test health data tools without any real PHI.

## What this project does

1. **`parse_fhir_bundles.py`** — reads all 555 raw FHIR bundles (one JSON file per
   patient) and flattens them into 8 clean tables (patients, encounters, conditions,
   observations, medication requests, immunizations, procedures, allergies), preserving
   which medical coding system each record uses.
2. **`notebooks/01_data_quality_audit.ipynb`** — audits the parsed data for the issues
   that matter most in real-world EHR interoperability: missing fields, inconsistent or
   missing coding systems, broken references between resources, and duplicate IDs.
3. **`notebooks/02_population_health_and_care_gaps.ipynb`** — uses the same data to
   answer population-health questions: demographics, chronic disease prevalence,
   medication burden, and a concrete care-gap example (diabetics overdue for an HbA1c
   lab).

## Key findings

**Data quality / interoperability:**
- Coding system usage is fully consistent within each resource type: encounters,
  conditions, and procedures use SNOMED-CT exclusively; observations use LOINC
  exclusively; immunizations use CVX exclusively.
- Medication requests are 98.5% RxNorm-coded, with 1.5% (354 of 24,256) missing a
  coding system entirely — the one meaningful gap found.
- Allergies mix SNOMED-CT (92.8%) and RxNorm (7.2%), which is expected — allergies can
  be recorded either as a clinical finding or as a reaction to a specific substance.
- Referential integrity is fully intact: zero orphaned patient or encounter references
  across all ~248,000 clinical records, and zero duplicate resource IDs in any table.

**Population health:**
- 555 patients, 54% female / 46% male, ages 0–110 (mean 42), all located in
  Massachusetts (a known characteristic of Synthea's default sample population, not a
  data quality issue).
- Most prevalent conditions include viral sinusitis, prediabetes, acute bronchitis,
  hypertension, and obesity (BMI 30+) — alongside social-determinants findings like
  stress, social isolation, and unemployment, which Synthea also models.
- 48.6% of patients have 5 or more distinct medications on record.
- **Care gap:** 165 patients (29.7%) are identified as diabetic or prediabetic; of the
  patients with a diabetes diagnosis, 23% (38 patients) have no HbA1c lab result in the
  trailing 12 months of their record — a standard diabetes-management quality measure
  they'd be flagged for in a real population-health outreach program.
- Flu vaccine coverage is 98.6%; childhood-only vaccines (MMR, varicella, HPV) show
  ~15% coverage, which reflects the mixed-age population rather than a true gap.

## Tech stack

Python, pandas, Jupyter, matplotlib, seaborn. 

## Why this project

Most public health data portfolios work with already-tabular data (CSVs, SQL tables).
This project starts one level lower, parsing the actual data *format* that EHR systems
exchange in the real world, to demonstrate comfort with healthcare data standards
(FHIR, SNOMED-CT, LOINC, RxNorm, CVX, ICD-10) that show up constantly in health IT and
health data analyst roles, not just the analysis layer on top of them.
