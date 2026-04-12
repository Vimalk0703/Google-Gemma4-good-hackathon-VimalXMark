# Malaika — Testing Strategy

> If it's not tested, it doesn't work. If it's not measured, it's not accurate.

---

## 1. Testing Pyramid

```
                    ┌───────────────────┐
                    │   E2E / Demo      │  Manual: full assessment flow
                    │   (few, manual)   │  before every submission milestone
                    ├───────────────────┤
                    │   Integration     │  IMCI engine + inference mock
                    │   (moderate)      │  State machine + perception parsing
                    ├───────────────────┤
                    │   Medical         │  WHO protocol: threshold accuracy
                    │   Accuracy        │  20+ clinical scenarios
                    │   (comprehensive) │  Classification correctness
                    ├───────────────────┤
                    │   Unit Tests      │  Every module, every function
                    │   (many, fast)    │  No GPU needed, mocked inference
                    └───────────────────┘
```

---

## 2. Unit Tests

### Scope
Every public function in every module has at least one test. Unit tests are fast (no GPU, no model loading) and run on every change.

### Conventions

```python
# File: tests/test_imci_protocol.py

import pytest
from malaika.imci_protocol import classify_breathing, BreathingClassification


class TestClassifyBreathing:
    """Tests for WHO IMCI breathing classification logic."""

    def test_fast_breathing_infant_2_to_11_months(self) -> None:
        """50+ breaths/min in 2-11 month old = fast breathing (WHO IMCI p.5)."""
        result = classify_breathing(rate=55, age_months=6)
        assert result == BreathingClassification.FAST_BREATHING

    def test_normal_breathing_infant_2_to_11_months(self) -> None:
        """<50 breaths/min in 2-11 month old = normal."""
        result = classify_breathing(rate=42, age_months=6)
        assert result == BreathingClassification.NORMAL

    def test_fast_breathing_child_12_to_59_months(self) -> None:
        """40+ breaths/min in 12-59 month old = fast breathing (WHO IMCI p.5)."""
        result = classify_breathing(rate=45, age_months=24)
        assert result == BreathingClassification.FAST_BREATHING

    def test_boundary_exactly_at_threshold(self) -> None:
        """Exactly at threshold = fast breathing (>= not >)."""
        result = classify_breathing(rate=50, age_months=6)
        assert result == BreathingClassification.FAST_BREATHING

    def test_invalid_age_raises(self) -> None:
        """Age outside 2-59 months raises ValueError."""
        with pytest.raises(ValueError, match="age_months must be between 2 and 59"):
            classify_breathing(rate=40, age_months=1)
```

### Naming Convention
- Test files: `test_<module>.py`
- Test classes: `Test<FunctionOrClass>`
- Test methods: `test_<behavior_being_tested>`
- Use descriptive names — the test name IS the documentation

### What to Test in Unit Tests
- All WHO threshold boundaries (exact, one above, one below)
- All IMCI classification paths
- All state machine transitions
- All perception result parsing (valid, invalid, edge cases)
- Config loading and feature flags
- Error cases (invalid input, missing files)

### What NOT to Test in Unit Tests
- Gemma 4 model output quality (that's medical accuracy testing)
- Gradio UI rendering (that's manual E2E)
- GPU/CUDA behavior (that's integration)

---

## 3. Integration Tests

### Scope
Test module interactions with mocked inference. Verify the IMCI engine correctly orchestrates perception modules and protocol logic.

```python
# File: tests/test_imci_integration.py

class TestIMCIEngineIntegration:
    """Integration tests for full IMCI assessment flow."""

    def test_full_assessment_no_danger_signs(self, mock_inference) -> None:
        """Complete assessment with no danger signs produces GREEN classification."""
        engine = IMCIEngine(inference=mock_inference)
        # Simulate all inputs for a healthy child
        engine.submit_danger_signs(image=healthy_child_image)
        engine.submit_breathing(video=normal_breathing_video)
        engine.submit_diarrhea(responses=no_diarrhea_responses)
        engine.submit_fever(responses=no_fever_responses)
        engine.submit_nutrition(image=normal_nutrition_image)

        result = engine.classify()
        assert result.severity == Severity.GREEN
        assert result.referral_urgency == ReferralUrgency.NONE

    def test_danger_sign_forces_urgent(self, mock_inference) -> None:
        """Any danger sign detected -> URGENT referral regardless of other findings."""
        engine = IMCIEngine(inference=mock_inference)
        engine.submit_danger_signs(image=lethargic_child_image)  # Mock returns lethargic=True
        # ... complete remaining steps ...

        result = engine.classify()
        assert result.severity == Severity.RED
        assert result.referral_urgency == ReferralUrgency.IMMEDIATE
```

### Mock Inference Strategy

```python
# tests/conftest.py

@pytest.fixture
def mock_inference():
    """Mock MalaikaInference that returns predetermined responses."""
    inference = MagicMock(spec=MalaikaInference)
    # Default: return safe/normal responses
    inference.analyze_image.return_value = "The child appears alert and responsive."
    inference.analyze_audio.return_value = "Normal breath sounds, no wheeze or stridor."
    inference.reason.return_value = "No treatment needed. Child is healthy."
    return inference
```

---

## 4. Medical Accuracy Tests

### Purpose
Validate that the complete system (Gemma 4 + protocol logic) produces correct WHO IMCI classifications for known clinical scenarios. These require a GPU and a loaded model.

### Test Scenarios (20+ required for submission)

| # | Scenario | Expected Classification | Key Test |
|---|----------|------------------------|----------|
| 1 | Fast breathing (55/min), 6mo, no other signs | PNEUMONIA (Yellow) | Breathing rate threshold |
| 2 | Chest indrawing + stridor at rest | SEVERE PNEUMONIA (Red) | Vision + audio combined |
| 3 | Watery diarrhea 3 days, slow skin pinch | SOME DEHYDRATION (Yellow) | Dehydration classification |
| 4 | Bloody diarrhea | DYSENTERY (Yellow) | Single symptom classification |
| 5 | Unable to drink, lethargic | URGENT REFERRAL (Red) | Danger sign override |
| 6 | Fever 5 days, malaria area | MALARIA (Yellow) | Contextual reasoning |
| 7 | Cough 3 days, normal breathing rate | COUGH/COLD (Green) | Normal finding |
| 8 | Vomiting everything | URGENT REFERRAL (Red) | Danger sign |
| 9 | Jaundiced skin (neonatal) | JAUNDICE (Yellow) | Fine-tuned vision |
| 10 | Severe visible wasting | SEVERE MALNUTRITION (Red) | Vision assessment |
| 11 | MUAC < 115mm | SEVERE MALNUTRITION (Red) | Threshold boundary |
| 12 | Wheezing, normal rate | WHEEZE (Green) | Audio only finding |
| 13 | Convulsions reported | URGENT REFERRAL (Red) | Danger sign |
| 14 | Fever + stiff neck | VERY SEVERE FEBRILE DISEASE (Red) | Combined danger |
| 15 | Sunken eyes + restless | SOME DEHYDRATION (Yellow) | Multiple dehydration signs |
| 16 | Edema both feet | SEVERE MALNUTRITION (Red) | Nutrition assessment |
| 17 | Normal child, all clear | HEALTHY (Green) | Happy path |
| 18 | Fast breathing + chest indrawing | SEVERE PNEUMONIA (Red) | Escalation logic |
| 19 | Diarrhea 14+ days | PERSISTENT DIARRHEA (Yellow) | Duration threshold |
| 20 | Measles within last 3 months | MEASLES COMPLICATIONS (Yellow) | History reasoning |

### Running Medical Accuracy Tests

```bash
# Requires GPU and loaded model — slow, run deliberately
pytest tests/test_medical_accuracy.py -v --gpu-required

# Generate accuracy report
pytest tests/test_medical_accuracy.py --accuracy-report=reports/accuracy.json
```

### Accuracy Targets

| Component | Target | Measurement |
|-----------|--------|-------------|
| IMCI classification (deterministic logic) | 100% | Unit tests on protocol.py |
| Breathing rate from video | +/- 5 breaths/min | Compare vs expert ground truth |
| Breath sound classification | > 80% accuracy | ICBHI test split |
| Jaundice detection | > 75% sensitivity | Mendeley/NJN test split |
| Speech understanding (English) | > 90% intent accuracy | Manual evaluation |
| Speech understanding (Swahili) | > 70% intent accuracy | Manual evaluation |
| Chest indrawing detection | > 75% sensitivity | Clinical image test set |

---

## 5. Performance Benchmarks

### What to Measure

```python
# tests/test_benchmarks.py

class TestInferenceBenchmarks:
    """Performance benchmarks — run with: pytest tests/test_benchmarks.py -v --benchmark"""

    def test_image_analysis_latency(self, loaded_inference, sample_image) -> None:
        """Image analysis must complete within 10 seconds."""
        start = time.monotonic()
        loaded_inference.analyze_image(sample_image, "Describe this image.")
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"Image analysis took {elapsed:.1f}s (budget: 10s)"

    def test_vram_usage_within_budget(self, loaded_inference) -> None:
        """Model must use less than 8GB VRAM."""
        vram_mb = torch.cuda.memory_allocated() / 1024 / 1024
        assert vram_mb < 8192, f"VRAM usage: {vram_mb:.0f}MB (budget: 8192MB)"
```

### Benchmark Table (updated as we test)

| Metric | Budget | Actual | Status |
|--------|--------|--------|--------|
| Model load time | < 60s | TBD | Pending Day 2 |
| VRAM usage (E4B 4-bit) | < 8 GB | TBD | Pending Day 2 |
| Image analysis latency | < 10s | TBD | Pending Day 2 |
| Audio analysis latency | < 15s | TBD | Pending Day 2 |
| Video analysis latency | < 30s | TBD | Pending Day 2 |
| TTS generation | < 3s | TBD | Pending |
| Full assessment (7 steps) | < 5 min | TBD | Pending |

---

## 6. Test Infrastructure

### Fixtures (tests/conftest.py)

```python
# Shared test fixtures

@pytest.fixture(scope="session")
def loaded_inference():
    """Load real Gemma 4 model once for GPU-required tests."""
    # Only loads if --gpu-required flag is passed
    return MalaikaInference(model_name="google/gemma-4-E4B-it", quantize_4bit=True)

@pytest.fixture
def mock_inference():
    """Fast mock for unit tests."""
    return create_mock_inference()

@pytest.fixture
def sample_images(tmp_path):
    """Sample clinical images for testing."""
    return load_test_images(tmp_path)

@pytest.fixture
def sample_audio(tmp_path):
    """Sample audio clips for testing."""
    return load_test_audio(tmp_path)
```

### Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "gpu_required: test requires GPU and loaded model (slow)",
    "medical_accuracy: clinical scenario validation",
    "benchmark: performance benchmark",
    "integration: integration test with mocked inference",
]
```

### Running Tests

```bash
# Fast: unit tests only (no GPU needed)
pytest tests/ -v -m "not gpu_required"

# Full: everything including GPU tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=malaika --cov-report=term-missing --cov-fail-under=80

# Medical accuracy only
pytest tests/ -v -m medical_accuracy

# Benchmarks only
pytest tests/ -v -m benchmark
```

---

## 7. Coverage Targets

| Module | Minimum Coverage | Rationale |
|--------|-----------------|-----------|
| `imci_protocol.py` | 100% | Medical safety — every path must be tested |
| `imci_engine.py` | 90% | Core orchestration logic |
| `types.py` | 100% | Data contracts |
| `config.py` | 90% | Configuration correctness |
| `vision.py` | 80% | Parsing logic (model output varies) |
| `audio.py` | 80% | Parsing logic (model output varies) |
| `inference.py` | 70% | Heavy GPU dependency, some paths hard to unit test |
| `app.py` | 60% | UI layer, tested manually |
| **Overall** | **80%** | |

---

## 8. Pre-Submission Checklist

Before every phase milestone and before final submission:

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `pytest tests/ --cov=malaika --cov-fail-under=80` — coverage met
- [ ] `mypy malaika/ --strict` — no type errors
- [ ] `ruff check malaika/ tests/` — no lint errors
- [ ] Medical accuracy: 20+ scenarios documented with results
- [ ] Performance benchmarks: all within budget
- [ ] Manual E2E: run full assessment flow in Gradio, verify output
- [ ] Offline test: disable network, run full assessment
