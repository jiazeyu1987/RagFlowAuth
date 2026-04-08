# Training Compliance Refactor Phase 1

## Context

The next bounded refactor hotspot after the completed system plan is training compliance.

Current hotspots:

- `backend/services/training_compliance.py` mixes validation helpers, serializers, read queries,
  writes, and authorization evaluation in one backend service file.
- `fronted/src/pages/TrainingComplianceManagement.js` mixes page shell, static copy/config, lookup
  widget rendering, and both major tab panel render trees in one page file.
- `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js` duplicates user-search
  effect logic and owns broad page orchestration in one hook.

The module already has focused backend and frontend tests, which makes it a good candidate for a
bounded, behavior-preserving refactor.

## In Scope

- backend training-compliance service decomposition
- frontend training-compliance page and hook decomposition
- focused backend/frontend regression tests

## Out Of Scope

- changing API paths or response envelopes
- changing business rules for qualification or certification
- redesigning the training-compliance UI
- touching unrelated user-search infrastructure outside this module

## Refactor Direction

1. Keep `TrainingComplianceService` as the stable backend facade, but extract validation,
   serialization, and data-access/orchestration helpers into bounded modules.
2. Keep `TrainingComplianceManagement` as the stable page entry, but extract reusable lookup and
   tab-panel rendering into focused components/helpers.
3. Extract duplicated frontend user-search behavior out of `useTrainingCompliancePage`.
4. Preserve all current test ids, router semantics, and fail-fast behavior.

## Acceptance Criteria

1. Backend training-compliance logic is no longer concentrated in one monolithic service file.
2. Frontend page and hook are no longer single-file owners of all training-compliance rendering and
   user-search logic.
3. Focused backend and frontend training-compliance tests pass after the refactor.

## Validation

- `python -m pytest backend/tests/test_training_compliance_api_unit.py`
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/trainingCompliance/useTrainingCompliancePage.test.js src/pages/TrainingComplianceManagement.test.js`
