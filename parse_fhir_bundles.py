"""
parse_fhir_bundles.py

Reads every Synthea-generated FHIR R4 patient bundle in data/raw_fhir/fhir/
and flattens the resources inside each bundle into clean, tabular CSVs —
one CSV per FHIR resource type — written to data/processed/.

This is synthetic data (no real patients), so there's no privacy concern
with committing data/processed/ to a public repo. The raw bundles themselves
are gitignored anyway, just to keep the repo small (555 JSON files, ~95MB).

Each patient bundle is a FHIR "Bundle" resource containing many "entry"
objects, each wrapping one clinical resource (Condition, Observation,
Encounter, etc). This script pulls out the resource types most relevant to
a data-quality / interoperability audit, and for each one records which
coding system was used (SNOMED-CT, LOINC, RxNorm, ICD-10-CM, CVX) alongside
the code and human-readable display text — that coding-system field is the
whole point: it's what lets us audit standards coverage later.

Two files in the raw folder are NOT patient bundles and are skipped:
  - hospitalInformation*.json
  - practitionerInformation*.json

Usage:
    python parse_fhir_bundles.py
"""

import json
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw_fhir/fhir")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP_PREFIXES = ("hospitalInformation", "practitionerInformation")

patient_files = [
    f for f in RAW_DIR.glob("*.json")
    if not f.name.startswith(SKIP_PREFIXES)
]

if not patient_files:
    raise FileNotFoundError(
        f"No patient bundle files found in {RAW_DIR}. "
        "Check that the Synthea sample data was unzipped there."
    )

print(f"Found {len(patient_files)} patient bundle files. Parsing...")

# One list per resource type we care about — each list holds one dict per
# resource instance, across ALL patients.
patients = []
encounters = []
conditions = []
observations = []
medication_requests = []
immunizations = []
procedures = []
allergies = []


def first_coding(codeable_concept):
    """Pull system/code/display from the first coding entry, if present."""
    if not codeable_concept:
        return {"code_system": None, "code": None, "code_display": None, "n_codings": 0}
    codings = codeable_concept.get("coding", [])
    if not codings:
        return {
            "code_system": None,
            "code": None,
            "code_display": codeable_concept.get("text"),
            "n_codings": 0,
        }
    c = codings[0]
    return {
        "code_system": c.get("system"),
        "code": c.get("code"),
        "code_display": c.get("display") or codeable_concept.get("text"),
        "n_codings": len(codings),
    }


def ref_id(reference_obj):
    """FHIR references look like 'urn:uuid:<id>' or 'Patient/<id>' — grab just the id."""
    if not reference_obj or "reference" not in reference_obj:
        return None
    return reference_obj["reference"].split(":")[-1].split("/")[-1]


for file in patient_files:
    with open(file, "r") as f:
        bundle = json.load(f)

    entries = bundle.get("entry", [])
    for entry in entries:
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            ext = {e.get("url", "").split("/")[-1]: e for e in resource.get("extension", [])}
            patients.append({
                "patient_id": resource.get("id"),
                "birth_date": resource.get("birthDate"),
                "gender": resource.get("gender"),
                "deceased": resource.get("deceasedDateTime") is not None,
                "marital_status": (resource.get("maritalStatus") or {}).get("text"),
                "language": (resource.get("communication", [{}])[0]
                             .get("language", {}).get("text")
                             if resource.get("communication") else None),
                "state": next(
                    (a.get("state") for a in resource.get("address", []) if a.get("state")),
                    None,
                ),
                "city": next(
                    (a.get("city") for a in resource.get("address", []) if a.get("city")),
                    None,
                ),
            })

        elif rtype == "Encounter":
            coding = first_coding(resource.get("type", [{}])[0] if resource.get("type") else None)
            period = resource.get("period", {})
            encounters.append({
                "encounter_id": resource.get("id"),
                "patient_id": ref_id(resource.get("subject")),
                "status": resource.get("status"),
                "class": (resource.get("class") or {}).get("code"),
                "start": period.get("start"),
                "end": period.get("end"),
                **coding,
            })

        elif rtype == "Condition":
            coding = first_coding(resource.get("code"))
            conditions.append({
                "condition_id": resource.get("id"),
                "patient_id": ref_id(resource.get("subject")),
                "encounter_id": ref_id(resource.get("encounter")),
                "clinical_status": (resource.get("clinicalStatus") or {}).get("coding", [{}])[0].get("code"),
                "onset_date": resource.get("onsetDateTime"),
                "abatement_date": resource.get("abatementDateTime"),
                **coding,
            })

        elif rtype == "Observation":
            coding = first_coding(resource.get("code"))
            value = resource.get("valueQuantity", {})
            observations.append({
                "observation_id": resource.get("id"),
                "patient_id": ref_id(resource.get("subject")),
                "encounter_id": ref_id(resource.get("encounter")),
                "effective_date": resource.get("effectiveDateTime"),
                "value": value.get("value"),
                "unit": value.get("unit"),
                "category": (resource.get("category", [{}])[0]
                             .get("coding", [{}])[0].get("code")
                             if resource.get("category") else None),
                **coding,
            })

        elif rtype == "MedicationRequest":
            med_concept = resource.get("medicationCodeableConcept")
            coding = first_coding(med_concept)
            medication_requests.append({
                "medication_request_id": resource.get("id"),
                "patient_id": ref_id(resource.get("subject")),
                "encounter_id": ref_id(resource.get("encounter")),
                "status": resource.get("status"),
                "authored_on": resource.get("authoredOn"),
                **coding,
            })

        elif rtype == "Immunization":
            coding = first_coding(resource.get("vaccineCode"))
            immunizations.append({
                "immunization_id": resource.get("id"),
                "patient_id": ref_id(resource.get("patient")),
                "encounter_id": ref_id(resource.get("encounter")),
                "status": resource.get("status"),
                "date": resource.get("occurrenceDateTime"),
                **coding,
            })

        elif rtype == "Procedure":
            coding = first_coding(resource.get("code"))
            procedures.append({
                "procedure_id": resource.get("id"),
                "patient_id": ref_id(resource.get("subject")),
                "encounter_id": ref_id(resource.get("encounter")),
                "status": resource.get("status"),
                "performed_date": resource.get("performedDateTime")
                or (resource.get("performedPeriod") or {}).get("start"),
                **coding,
            })

        elif rtype == "AllergyIntolerance":
            coding = first_coding(resource.get("code"))
            allergies.append({
                "allergy_id": resource.get("id"),
                "patient_id": ref_id(resource.get("patient")),
                "recorded_date": resource.get("recordedDate"),
                **coding,
            })

# ---------------------------------------------------------------------------
# Write each resource type to its own CSV
# ---------------------------------------------------------------------------
tables = {
    "patients": patients,
    "encounters": encounters,
    "conditions": conditions,
    "observations": observations,
    "medication_requests": medication_requests,
    "immunizations": immunizations,
    "procedures": procedures,
    "allergies": allergies,
}

print()
for name, rows in tables.items():
    df = pd.DataFrame(rows)
    out_path = OUT_DIR / f"{name}.csv"
    df.to_csv(out_path, index=False)
    print(f"{name:22s} {len(df):>7,} rows  -> {out_path}")

print(f"\nDone. All tables written to {OUT_DIR}/")
