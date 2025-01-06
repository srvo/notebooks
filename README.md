# Research Notebooks

This directory contains Jupyter notebooks and Python modules for running and managing research search flows.

## Project Structure

```
notebooks/
├── config.py                   # Central configuration
├── logger.py                   # Logging setup
├── api_client.py               # API interaction module
├── data_store.py               # Data storage and S3 backup module
├── jupyter/
│   ├── search_flow.py          # Core search implementation
│   ├── reset_research.py       # Database reset utility
│   ├── run_background_search.py # Background process runner
│   └── research/
│       ├── workflow.py         # Workflow management system
│       └── example_workflow.py # Example workflow usage
├── logs/                       # Process logs
├── data/
│   ├── research.db             # Research database
│   └── backups/                # S3 backups
└── README.md                   # Project documentation
```

## Quick Start

Run search flow in the background (preserves existing data):
```bash
python jupyter/run_background_search.py &
```

Run with database reset (caution - clears existing research):
```bash
python jupyter/run_background_search.py --reset &
```

Run example workflow:
```bash
python jupyter/research/example_workflow.py
```

## Workflow System

The workflow system provides a way to define and execute multi-phase workflows:

```python
from jupyter.research.workflow import Workflow, WorkflowPhase

# Define phases
phases = [
    WorkflowPhase(name="Fetch Data", task=fetch_data),
    WorkflowPhase(name="Process Data", task=process_data),
    WorkflowPhase(name="Save Data", task=save_data)
]

# Create and execute workflow
workflow = Workflow(phases, n_jobs=1)
results = workflow.execute()

# Observe progress
for result in workflow.observe():
    print(result)
```

## Configuration

Update the `config.py` file with your API keys, database URI, and AWS credentials.

## Logs

All logs are stored in the `logs/` directory with timestamped filenames:
- `run_background_search.log`
- `api_client.log`
- `data_store.log`
- `workflow.log`
- `example_workflow.log`


