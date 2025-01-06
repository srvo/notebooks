import logging
from research.workflows.ethical import EthicalAnalysisWorkflow

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    workflow = EthicalAnalysisWorkflow()
    workflow.execute() 