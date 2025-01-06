import asyncio
from research.engines.api_docs import APIDocEngine
import json

async def main():
    engine = APIDocEngine()
    print("\nDiscovering complementary data sources and services...\n")
    
    # Get suggestions for additional services
    suggestions = await engine.discover_complementary_services()
    
    # Print formatted results
    for api in suggestions['suggested_apis']:
        print(f"\n=== {api['name']} ===")
        print(f"URL: {api['url']}")
        print(f"Description: {api['description']}")
        
        print("\nUnique Value:")
        for value in api['unique_value']:
            print(f"  - {value}")
            
        print("\nData Coverage:")
        if 'coverage' in api:
            print(f"  Historical Range: {api['coverage']['historical_range']}")
            print(f"  Update Frequency: {api['coverage']['update_frequency']}")
            print("  Geographical Coverage:", ", ".join(api['coverage']['geographical']))
            
        print("\nData Types:")
        if api['data_types']['categories']:
            print("  Categories:", ", ".join(api['data_types']['categories']))
        if api['data_types']['fields']:
            print("  Fields:", ", ".join(api['data_types']['fields']))
        if api['data_types']['formats']:
            print("  Formats:", ", ".join(api['data_types']['formats']))
            
        print("\nData Quality:")
        if 'data_quality' in api:
            print(f"  Verification: {api['data_quality']['verification_process']}")
            print(f"  Source Citations: {'Yes' if api['data_quality']['source_citations'] else 'No'}")
            print(f"  Standardization: {api['data_quality']['standardization']}")
            
        print("\nAccess Methods:", ", ".join(api['access_methods']))
        
        if api['rate_limits']:
            print("\nRate Limits:", json.dumps(api['rate_limits'], indent=2))
            
        print(f"\nPricing: {api['pricing_notes']}")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main()) 