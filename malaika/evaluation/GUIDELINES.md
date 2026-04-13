# evaluation/ — Evaluation Skill

> If it's not measured, it's not accurate. Ship blind and children pay the price.

---

## What This Module Does

Provides offline evaluation of the entire Malaika system against a golden dataset of 20+ WHO IMCI clinical scenarios with known-correct classifications.

This module provides:
- **Golden scenarios** (`golden_scenarios.py`): 20+ test cases with expected WHO classifications
- **Evaluator** (`evaluator.py`): Run model against golden set, produce accuracy reports

The evaluation framework answers one question: **"Does Malaika classify this child correctly according to WHO IMCI?"**

## What This Module Does NOT Do

- Does NOT define WHO thresholds (that's `imci_protocol.py`)
- Does NOT run unit tests (that's `tests/`)
- Does NOT train models (that's `scripts/`)
- Does NOT replace manual clinical validation

---

## Rules

### R1: Golden Scenarios Are Ground Truth
Each scenario has a **known-correct classification** derived from the WHO IMCI Chart Booklet. These are not opinions — they are the protocol. If the system disagrees with a golden scenario, the system is wrong.

### R2: Scenarios Cover All Classification Paths
Every `ClassificationType` in `types.py` must be exercised by at least one golden scenario. No dead paths.

### R3: Scenarios Are Layered
Three levels of scenarios:

| Level | What It Tests | Example |
|-------|--------------|---------|
| **Protocol-only** | `imci_protocol.py` with hardcoded inputs | `classify_breathing(rate=55, age=6)` -> `PNEUMONIA` |
| **Perception + Protocol** | Gemma 4 output parsing + protocol logic | Image of chest indrawing -> parse -> classify |
| **End-to-end** | Full IMCI flow from raw media to classification | Video + audio + text -> complete assessment |

Protocol-only scenarios run fast (no GPU). Perception scenarios need mock inference. End-to-end needs real model.

### R4: Every Scenario Documents Its WHO Source
Each scenario cites the specific WHO IMCI Chart Booklet page or decision table that defines the expected classification.

```python
GoldenScenario(
    name="fast_breathing_infant",
    description="55 breaths/min in 6-month-old with cough",
    who_source="IMCI Chart Booklet, p.5: Breathing thresholds by age",
    ...
)
```

### R5: Accuracy Reports Are Versioned
Each evaluation run produces a dated report with:
- Model version / adapter version
- Prompt versions used (from traces)
- Per-scenario pass/fail
- Aggregate accuracy by category (breathing, diarrhea, fever, etc.)
- Regression detection (did accuracy drop since last run?)

### R6: Run Evaluation Before Every Milestone
Before Phase 2, 3, 4, and submission milestones — run the full golden set. No exceptions. Results go in the writeup.

---

## Golden Scenario Format

```python
@dataclass(frozen=True)
class GoldenScenario:
    """A single evaluation scenario with known-correct WHO classification."""

    # Identity
    name: str                       # Unique snake_case identifier
    description: str                # Human-readable scenario description
    who_source: str                 # WHO IMCI citation

    # Input (what the child presents with)
    age_months: int
    findings: dict[str, Any]        # Structured findings per IMCI step
    # e.g., {"breathing_rate": 55, "has_indrawing": True, "has_wheeze": False}

    # Expected output
    expected_classifications: list[ClassificationType]
    expected_severity: Severity
    expected_referral: ReferralUrgency

    # Test level
    level: str = "protocol"  # "protocol", "perception", "e2e"

    # Optional: media paths for perception/e2e tests
    test_image: str | None = None
    test_audio: str | None = None
    test_video: str | None = None
```

---

## Minimum Scenario Coverage

| IMCI Domain | Min Scenarios | Must Cover |
|-------------|---------------|------------|
| Danger signs | 3 | Lethargic, convulsions, unable to drink |
| Breathing | 4 | Normal, fast, indrawing, stridor |
| Diarrhea | 4 | None, some dehydration, severe, dysentery |
| Fever | 3 | No fever, malaria risk, very severe febrile |
| Nutrition | 3 | Normal, moderate wasting, severe + edema |
| Heart (MEMS) | 1 | Normal (or disabled path) |
| Combined | 3 | Multi-domain scenarios (e.g., pneumonia + dehydration) |
| **Total** | **21+** | |

---

## Running Evaluation

```bash
# Protocol-only (fast, no GPU)
python -m malaika.evaluation.evaluator --level protocol

# With perception mocks (moderate, no GPU)
python -m malaika.evaluation.evaluator --level perception

# Full end-to-end (slow, needs GPU)
python -m malaika.evaluation.evaluator --level e2e

# Generate report
python -m malaika.evaluation.evaluator --level protocol --report reports/eval_$(date +%Y%m%d).json
```

---

## File Inventory

| File | Component | Responsibility |
|------|-----------|----------------|
| `__init__.py` | Module | Exports `GoldenScenario`, `Evaluator` |
| `golden_scenarios.py` | Golden Set | 20+ scenarios with expected WHO classifications |
| `evaluator.py` | Evaluator | Run scenarios, compare results, produce accuracy report |
