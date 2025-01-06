from search_flow import ResearchWorkflow, get_top_companies, get_research_status
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('research_workflow.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Run research workflow on top companies"""
    logging.info("Starting research workflow")
    
    # Get top 5 companies
    companies = get_top_companies(limit=150)
    logging.info(f"Retrieved {len(companies)} companies to research")
    
    # Initialize workflow
    workflow = ResearchWorkflow(timeout=30)  # Increased timeout for reliability
    
    # Process each company
    for company in companies:
        logging.info(f"Processing {company['name']} ({company['ticker']})")
        result = workflow.research_company(company)
        if result:
            logging.info(f"Successfully processed {company['name']}")
            logging.info(f"Risk score: {result['structured_data'].get('risk_score')}")
            logging.info(f"Recommendation: {result['structured_data'].get('recommendation')}")
        else:
            logging.error(f"Failed to process {company['name']}")
    
    # Get final status
    status = get_research_status()
    logging.info("Research workflow status:")
    logging.info(f"Total companies: {status['total']}")
    logging.info(f"Completed: {status['completed']}")
    logging.info(f"In progress: {status['in_progress']}")
    logging.info(f"Failed: {status['failed']}")
    logging.info(f"Not started: {status['not_started']}")
    logging.info(f"Completion percentage: {status['completion_percentage']:.2f}%")

if __name__ == "__main__":
    main() 