# Requirement Delta: Mock Mode Removal

## REMOVED Requirements
### Requirement: Mock Mode Execution
- **Scenario:** The frontend sends `mode=mock` and the AI agents generate predefined dummy outputs.
- Now, the mock route is completely unavailable and removed. Every generation defaults to the authentic API payload.

## ADDED Requirements
### Requirement: Richer Model Set Selection
- **Scenario:** User selects the dropdown for the LLM model to be used in real time generation.
- There should be a default list available like `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `o1-mini`, `o3-mini` in real mode if env is empty.

## MODIFIED Requirements
### Requirement: Upload CSV Constraint Check
- **Scenario:** The frontend only allows users to upload datasets and overrides when the `mode` parameter is `real`.
- Now, since `mock` mode is removed, uploads are universally permitted with no further conditional rendering related to mode restrictions.
