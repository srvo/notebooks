from joblib import Parallel, delayed
from typing import List, Dict, Callable, Generator
from logger import setup_logger

logger = setup_logger('workflow', 'logs/workflow.log')

class WorkflowPhase:
    """Represents a single phase in a workflow."""
    def __init__(self, name: str, task: Callable, args: Dict = None):
        self.name = name
        self.task = task
        self.args = args or {}
        logger.debug(f"Created workflow phase: {self.name}")

    def execute(self):
        """Execute the phase's task."""
        try:
            logger.info(f"Executing phase: {self.name}")
            result = self.task(**self.args)
            logger.info(f"Completed phase: {self.name}")
            return result
        except Exception as e:
            logger.error(f"Error in phase {self.name}: {e}")
            raise

class Workflow:
    """Manages a multi-phase workflow."""
    def __init__(self, phases: List[WorkflowPhase], n_jobs: int = 1):
        self.phases = phases
        self.n_jobs = n_jobs
        logger.debug(f"Created workflow with {len(self.phases)} phases")

    def execute(self) -> List:
        """Execute the workflow."""
        logger.info("Starting workflow execution")
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(phase.execute)() for phase in self.phases
        )
        logger.info("Workflow execution completed")
        return results

    def observe(self) -> Generator:
        """Observe the workflow's progress."""
        for phase in self.phases:
            logger.info(f"Observing phase: {phase.name}")
            yield phase.execute()
