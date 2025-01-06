I'll create the README file in your notebooks directory:

```python:notebooks/README.md
# Research Notebooks

This directory contains Jupyter notebooks and Python scripts for running research search flows.

## Background Search Process

The main script `jupyter/run_background_search.py` allows you to run search flows as background processes with logging.

### Quick Start

Run search flow in background (preserves existing data):
```bash
python jupyter/run_background_search.py &
```

Run with database reset (caution - clears existing research):
```bash
python jupyter/run_background_search.py --reset &
```

### Process Management

- Process ID (PID) is displayed when started
- Check if running: `ps -p <PID>`
- Stop process: `kill <PID>`

### Logs

All logs are stored in `logs/` directory with timestamp format:
- `search_flow_YYYYMMDD_HHMMSS.log`

## Directory Structure

```
notebooks/
├── data/               # Data storage
│   └── research.db     # Research database
├── jupyter/            # Python modules
│   ├── search_flow.py  # Core search implementation
│   ├── reset_research.py   # Database reset utility
│   └── run_background_search.py  # Background process runner
└── logs/              # Process logs
```

## Database Notes

The research database (`research.db`) contains three main tables:
- research_checkpoints
- research_sources
- research_results

By default, the background search preserves this data unless `--reset` flag is used.
```

The README has been created with clear, concise instructions focused on the search flow functionality and process management. Let me know if you'd like any adjustments to the content!
