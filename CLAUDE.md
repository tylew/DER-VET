# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DER-VET (Distributed Energy Resource - Valuation Estimation Tool) is an open-source platform developed by EPRI for optimizing the value of distributed energy resources. It extends StorageVET and supports solar (PV), wind, energy storage, demand response, EVs, ICE generators, CHP, and microgrid configurations.

## Commands

**Setup (Python 3.11.9 required):**
```bash
conda create -n dervet-venv python=3.11.9
conda activate dervet-venv
pip install -r requirements.txt
pip install -e ./storagevet   # storagevet is a local git submodule/dependency
```

**Run the model:**
```bash
python run_DERVET.py Model_Parameters_Template_DER.csv
python run_DERVET.py Model_Parameters_Template_DER.csv -v  # verbose
```

**Run tests:**
```bash
python -m pytest test
python -m pytest test/test_storagevet_features/  # specific subdirectory
```

## Architecture

### Inheritance Hierarchy

DER-VET extends StorageVET. The `storagevet/` directory contains the base library (installed as a local editable package). DER-VET classes in `dervet/` inherit from and override base classes in `storagevet/storagevet/`.

Key inheritance pairs:
- `DERVET` ← `storagevet.StorageVET`
- `DERVETParams` ← `storagevet.Params`
- `MicrogridScenario` ← `storagevet.Scenario`
- `MicrogridPOI` ← `storagevet.POI`
- `MicrogridServiceAggregator` ← `storagevet.ServiceAggregator`
- `MicrogridResult` ← `storagevet.Result`
- `dervet/MicrogridDER/*.py` ← `storagevet/storagevet/Technology/*.py`

### Execution Flow

```
run_DERVET.py
  → DERVET (dervet/DERVET.py)
      → DERVETParams: parse CSV/JSON parameters
      → MicrogridScenario (for each case):
          → MicrogridPOI: manage loads/grid constraints
          → MicrogridServiceAggregator: coordinate technologies & value streams
          → sizing_module(): size technologies via CVXPY optimization
          → optimize_problem_loop(): dispatch optimization via CVXPY
      → MicrogridResult: aggregate & export results
```

### Key Components

**`dervet/MicrogridDER/`** — DER technology implementations:
- Each class models a technology's physical behavior, costs, and constraints
- `ESSSizing.py`, `IntermittentResourceSizing.py`, `RotatingGeneratorSizing.py` handle sizing optimization

**`storagevet/storagevet/ValueStreams/`** — Value stream implementations (15+ types):
- Energy arbitrage (`DAEnergyTimeShift`, `EnergyTimeShift`)
- Grid services (`FrequencyRegulation`, `SpinningReserve`, `NonspinningReserve`)
- Demand management (`DemandChargeReduction`, `CoincidentPeakShaving`)
- Infrastructure (`Deferral`, `ResourceAdequacy`, `Backup`)
- `dervet/MicrogridValueStreams/Reliability.py` adds DER-VET-specific reliability

**`MicrogridScenario.TECH_CLASS_MAP` and `VS_CLASS_MAP`** — Dictionaries that map parameter keys to technology/value stream classes. Add new DER types or value streams here.

### Optimization Engine

CVXPY is used for all optimization. The problem is built by collecting constraints and objective terms from all active technologies and value streams, then solved with GLPK_MI or ECOS_BB solvers.

### Parameters

Input parameters come from CSV (`Model_Parameters_Template_DER.csv`) or JSON (`Model_Parameters_Template_DER.json`) files. JSON format supports sensitivity analysis (parameter sweeps). The schema for validation is in `storagevet/storagevet/Schema.json`.

### Financial Analysis

`CBA.py` (Cost-Benefit Analysis) performs project financial evaluation including NPV, taxes, depreciation, and incentives. It inherits from `storagevet/storagevet/Finances.py`.

## Data

- `data/` — Input timeseries CSVs/XLSXs (load profiles, PV generation, tariffs, battery cycle life curves)
- `Results/` — Output directories (timestamped per run, gitignored)
- `test/datasets/` and `test/model_params/` — Test fixtures
