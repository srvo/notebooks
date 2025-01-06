from jupyter.research.workflow import Workflow, WorkflowPhase
from jupyter.api_client import APIClient
from jupyter.data_store import DataStore
from jupyter.data_processor import DataProcessor
from logger import setup_logger

logger = setup_logger('example_workflow', 'logs/example_workflow.log')

# Define tasks for each phase
def fetch_data(query: str):
    api_client = APIClient()
    return api_client.fetch_data('search_endpoint', params={'query': query})

def process_data(data):
    processor = DataProcessor()
    return processor.process(data)

def save_data(processed_data):
    data_store = DataStore()
    data_store.save_to_db(processed_data)
    data_store.backup_to_s3('data/research.db')

# Define workflow phases
phases = [
    WorkflowPhase(name="Fetch Data", task=fetch_data, args={'query': 'test query'}),
    WorkflowPhase(name="Process Data", task=process_data),
    WorkflowPhase(name="Save Data", task=save_data)
]

# Create and execute the workflow
workflow = Workflow(phases, n_jobs=1)
results = workflow.execute()

# Observe the workflow's progress
for result in workflow.observe():
    logger.info(f"Phase result: {result}")
