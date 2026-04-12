# Malaika — Development Guidelines

> How we write, review, commit, and ship code. Follow these to maintain velocity and quality.

---

## 1. Environment Setup

### Prerequisites

- Python 3.11+ (3.12 preferred)
- CUDA 12.x + compatible NVIDIA driver (for GPU inference)
- Git 2.40+

### Initial Setup

```bash
# Clone and enter project
cd /path/to/deepmind-hackathon

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install runtime dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .

# Verify setup
pytest tests/ -v -m "not gpu_required"
mypy malaika/ --strict
ruff check malaika/ tests/
```

### Training Environment (separate)

```bash
# Only needed for fine-tuning, not for development
pip install -r requirements-train.txt
```

---

## 2. Code Style

### Formatter and Linter: Ruff

Single tool for both formatting and linting. Google-compatible style.

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # type-checking imports
    "RUF",  # ruff-specific
    "S",    # bandit security
    "PTH",  # pathlib
]
ignore = [
    "S101",  # assert used in tests
]

[tool.ruff.lint.isort]
known-first-party = ["malaika"]
```

### Type Checking: mypy

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = [
    "transformers.*",
    "torch.*",
    "gradio.*",
    "piper.*",
    "cv2.*",
    "bitsandbytes.*",
    "unsloth.*",
    "trl.*",
]
ignore_missing_imports = true
```

---

## 3. Python Style Guide

### General Rules

- **100 character line length** (Ruff enforces this)
- **4 spaces** for indentation (no tabs)
- **Absolute imports** only: `from malaika.inference import MalaikaInference`
- **No wildcard imports**: never `from malaika import *`
- **f-strings** for formatting (not `.format()` or `%`)
- **`Path`** from pathlib for all file paths (not `os.path`)
- **Dataclasses** for structured data (not dicts or NamedTuples)
- **Enums** for all finite sets of values (states, severities, classifications)

### Dataclasses Over Dicts

```python
# YES — typed, documented, IDE-friendly
@dataclass(frozen=True)
class BreathingAssessment:
    rate: int | None
    has_indrawing: bool
    has_stridor: bool
    has_wheeze: bool
    confidence: float
    raw_model_output: str

# NO — untyped, error-prone, no IDE support
breathing = {
    "rate": 55,
    "indrawing": True,
    "confidence": 0.85,
}
```

### Enums for States and Classifications

```python
from enum import Enum, auto

class IMCIState(Enum):
    DANGER_SIGNS = auto()
    BREATHING = auto()
    DIARRHEA = auto()
    FEVER = auto()
    NUTRITION = auto()
    HEART_MEMS = auto()
    CLASSIFY = auto()
    TREAT = auto()
    COMPLETE = auto()

class Severity(Enum):
    GREEN = "green"    # Home care
    YELLOW = "yellow"  # Specific treatment
    RED = "red"        # Urgent referral
```

### Function Design

- Functions do one thing
- Max 30 lines per function (guideline, not strict rule — use judgment)
- Max 4 parameters. More? Use a config dataclass.
- Return typed values. Never return `Any` or untyped dicts.
- Pure functions where possible (no side effects, same input -> same output)

```python
# YES — pure, typed, single purpose
def is_fast_breathing(rate: int, age_months: int) -> bool:
    """Check if breathing rate exceeds WHO IMCI threshold for age group."""
    if 2 <= age_months <= 11:
        return rate >= 50
    if 12 <= age_months <= 59:
        return rate >= 40
    raise ValueError(f"age_months must be between 2 and 59, got {age_months}")
```

---

## 4. Git Workflow

### Branch Strategy

```
main                    # Always deployable, passing all tests
  └── feat/<name>       # Feature branches
  └── fix/<name>        # Bug fix branches
  └── data/<name>       # Dataset prep branches
  └── train/<name>      # Training experiment branches
```

### Branch Naming

```
feat/imci-breathing-assessment
feat/gradio-ui-skeleton
fix/breathing-rate-parser-boundary
data/icbhi-instruction-pairs
train/breath-sound-lora-v1
```

### Commit Messages

**Format**: `<type>: <description>`

Types:
- `feat`: New feature or capability
- `fix`: Bug fix
- `refactor`: Code restructure, no behavior change
- `test`: Add or modify tests
- `docs`: Documentation changes
- `data`: Dataset preparation or changes
- `train`: Training scripts or experiments
- `chore`: Build, config, dependency changes

```
# Good
feat: add breathing rate extraction from video via Gemma 4
fix: correct WHO threshold for 12-59 month age group
test: add boundary tests for all IMCI classification thresholds
refactor: extract perception parsing into dedicated module
data: prepare ICBHI instruction pairs for LoRA training

# Bad
update code
fix stuff
WIP
changes
```

### Commit Discipline

- Commit early, commit often — small, logical units
- Every commit should pass `ruff check` and `mypy --strict`
- Never commit broken tests
- Never commit secrets, large files, or model weights
- Write commit messages in imperative mood ("add", not "added" or "adds")

---

## 5. File Organization Rules

### Where Things Go

| What | Where | Why |
|------|-------|-----|
| Runtime Python code | `malaika/` | Main package |
| Tests | `tests/` | Mirrors `malaika/` structure |
| One-off scripts | `scripts/` | Data prep, benchmarks, exports |
| LoRA adapter weights | `adapters/` | Gitignored, downloaded/trained |
| Config files | `configs/` | YAML feature flags, model configs |
| Datasets | `data/` | Gitignored, downloaded via scripts |
| Documentation | `docs/` | Engineering docs |
| Planning docs | Project root | MASTERPLAN.md, PROPOSAL.md, etc. |

### Naming Rules

- Python files: `snake_case.py`
- Test files: `test_<matching_module>.py`
- Config files: `snake_case.yaml`
- Scripts: `<verb>_<noun>.py` (e.g., `download_datasets.py`, `prepare_icbhi.py`)
- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase`
- Everything else: `snake_case`

### Module Size Limits (guidelines)

- Max 300 lines per module (split if larger)
- Max 30 lines per function
- Max 10 methods per class
- If a module grows beyond these, extract a sub-module

---

## 6. Dependency Management

### Adding a Dependency

1. Verify it works offline
2. Check license compatibility (Apache 2.0, MIT, BSD)
3. Add to appropriate requirements file with pinned version
4. Update `.gitignore` if it creates cache/artifacts
5. Document why it's needed in a comment

```
# requirements.txt
transformers==4.52.0        # Gemma 4 model loading and inference
torch==2.6.0                # PyTorch backend for Transformers
bitsandbytes==0.45.0        # 4-bit quantization for GPU memory efficiency
accelerate==1.3.0           # Device mapping for multi-GPU / quantized models
gradio==5.25.0              # Web UI for demo
piper-tts==1.2.0            # Offline text-to-speech
opencv-python-headless==4.11.0  # Video frame extraction (headless = no GUI deps)
structlog==24.4.0           # Structured logging
```

### Upgrading a Dependency

1. Read the changelog
2. Run full test suite after upgrade
3. Update pinned version
4. Commit the upgrade separately from feature work

---

## 7. Pre-Commit Checks

Run before every commit:

```bash
# Format
ruff format malaika/ tests/

# Lint
ruff check malaika/ tests/ --fix

# Type check
mypy malaika/ --strict

# Tests (fast, no GPU)
pytest tests/ -v -m "not gpu_required" -x

# Security audit
pip audit
```

### Recommended: Git Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/sh
set -e
ruff format --check malaika/ tests/
ruff check malaika/ tests/
mypy malaika/ --strict
pytest tests/ -v -m "not gpu_required" -x --tb=short
```

---

## 8. Code Review Principles

Even in a hackathon, review your own code before committing:

1. **Does it match the architecture?** Check module boundaries (ARCHITECTURE.md)
2. **Is it typed?** `mypy --strict` must pass
3. **Is it tested?** New logic needs new tests
4. **Is it safe?** No clinical decisions in model calls (SECURITY.md)
5. **Is it necessary?** Don't gold-plate — ship the minimum that works correctly
6. **Is it offline?** No network calls in any code path

---

## 9. Documentation Standards

### Code Documentation
- Google-style docstrings on all public APIs
- WHO citations for every clinical threshold (page number if possible)
- No obvious comments (`# increment counter` — delete these)
- Comment the WHY, not the WHAT

### Project Documentation
- Update MASTERPLAN.md when sprint plans change
- Update ARCHITECTURE.md when module structure changes
- Keep README.md current for judges and reviewers
- Record test results and benchmarks with dates

---

## 10. Performance Profiling

When investigating performance:

```bash
# Profile a specific operation
python -m cProfile -s cumulative -m malaika.inference --profile

# Memory profiling
python -m memory_profiler scripts/profile_inference.py

# GPU memory monitoring
watch -n 1 nvidia-smi
```

Log these numbers. Update the benchmark table in TESTING_STRATEGY.md.
