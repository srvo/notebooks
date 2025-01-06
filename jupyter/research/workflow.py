from joblib import Parallel, delayed
from typing import List, Dict, Callable, Generator
from logger import setup_logger

logger = setup_logger('workflow', 'logs/workflow.log')

class WorkflowPhase:
    """
    Represents a single phase in a workflow.

    Attributes:
        name (str): The name of the phase.
        task (Callable): The function or method to execute for this phase.
        args (Dict): Arguments to pass to the task function.
    """

    def __init__(self, name: str, task: Callable, args: Dict = None):
        """
        Initialize a WorkflowPhase.

        Args:
            name (str): The name of the phase.
            task (Callable): The function or method to execute.
            args (Dict, optional): Arguments to pass to the task. Defaults to None.
        """
        self.name = name
        self.task = task
        self.args = args or {}
        logger.debug(f"Created workflow phase: {self.name}")

    def execute(self):
        """
        Execute the phase's task.

        Returns:
            Any: The result of the task execution.

        Raises:
            Exception: If the task execution fails.
        """
        try:
            logger.info(f"Executing phase: {self.name}")
            result = self.task(**self.args)
            logger.info(f"Completed phase: {self.name}")
            return result
        except Exception as e:
            logger.error(f"Error in phase {self.name}: {e}")
            raise

class Workflow:
    """
    Manages a multi-phase workflow.

    Attributes:
        phases (List[WorkflowPhase]): List of phases in the workflow.
        n_jobs (int): Number of parallel jobs for task execution.
    """

    def __init__(self, phases: List[WorkflowPhase], n_jobs: int = 1):
        """
        Initialize a Workflow.

        Args:
            phases (List[WorkflowPhase]): List of phases to execute.
            n_jobs (int, optional): Number of parallel jobs. Defaults to 1.
        """
        self.phases = phases
        self.n_jobs = n_jobs
        logger.debug(f"Created workflow with {len(self.phases)} phases")

    def execute(self) -> List:
        """
        Execute all phases in the workflow.

        Returns:
            List: Results of each phase's execution.

        Raises:
            Exception: If any phase fails during execution.
        """
        logger.info("Starting workflow execution")
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(phase.execute)() for phase in self.phases
        )
        logger.info("Workflow execution completed")
        return results

    def observe(self) -> Generator:
        """
        Observe the workflow's progress by executing phases one at a time.

        Yields:
            Any: The result of each phase's execution.
        """
        for phase in self.phases:
            logger.info(f"Observing phase: {phase.name}")
            yield phase.execute()
