from db import get_connection

def reset_research_data():
    """Reset all research-related database tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Delete data from research tables
        tables = ['research_checkpoints', 'research_sources', 'research_results']
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
                print(f'Cleared {table}')
            except Exception as e:
                print(f'Error clearing {table}: {str(e)}')
        
        conn.commit()
        print('Research data reset complete.')

if __name__ == "__main__":
    reset_research_data() 