import asyncio
from research.engines.api_docs import APIDocEngine

async def main():
    engine = APIDocEngine()
    print("Analyzing API documentation and available data types...\n")
    
    # Fetch documentation for all APIs
    docs = await engine.fetch_all_documentation()
    
    # Print data types and usage status for each API
    for api_name in engine.api_configs:
        status = await engine.get_commercial_usage_status(api_name)
        print(f"\n=== {api_name} ===")
        print("Data Types:")
        if status['data_types']:
            print("  Categories:", ", ".join(status['data_types']['categories']))
            print("  Fields:", ", ".join(status['data_types']['fields']))
            print("  Formats:", ", ".join(status['data_types']['formats']))
            print("  Special Features:", ", ".join(status['data_types']['special_features']))
        else:
            print("  No data type information available")
        print(f"Commercial Usage: {status['commercial_usage']}")
        print(f"Tier: {status['tier']}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 