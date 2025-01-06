import os
import requests
from typing import Dict, Optional, List, Tuple
import json
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging
from .base import BaseEngine
from datetime import datetime, timedelta
import aiohttp

@dataclass
class APIEndpoint:
    """Represents a single API endpoint with its metadata"""
    path: str           # The endpoint path (e.g., /v1/completions)
    method: str         # HTTP method (GET, POST, etc.)
    description: str    # Human-readable description
    parameters: Optional[Dict] = None         # Expected parameters
    response_format: Optional[Dict] = None    # Expected response format
    authentication: Optional[Dict] = None     # Auth requirements

@dataclass
class APIDocumentation:
    """Complete documentation for an API service"""
    name: str          # Service name (e.g., 'DEEPSEEK')
    base_url: str      # Base API URL
    auth_type: str     # Authentication type (Bearer, Basic, etc.)
    endpoints: List[APIEndpoint]  # List of available endpoints
    rate_limits: Optional[Dict] = None  # Rate limiting rules
    version: Optional[str] = None       # API version
    data_types: Optional[Dict] = None   # Types of data available
    commercial_usage: Optional[Dict] = None  # Basic commercial usage flags

class APIDocEngine(BaseEngine):
    """Engine for retrieving and formatting API documentation
    
    This engine fetches documentation from various API services,
    standardizes the format, and generates markdown documentation.
    
    Features:
    - Parallel documentation fetching
    - Rate limit tracking
    - Standardized output format
    - Markdown generation
    """
    
    def __init__(self):
        super().__init__()
        # Configuration for each API service we interact with
        self.api_configs = {
            'TAVILY_API_KEY': {
                'base_url': 'https://api.tavily.com/v1',
                'doc_url': 'https://docs.tavily.com',
                'auth_type': 'Bearer'
            },
            'BING_API_KEY': {
                'base_url': 'https://api.bing.microsoft.com',
                'doc_url': 'https://learn.microsoft.com/en-us/bing/search-apis',
                'auth_type': 'Bearer'
            },
            'OPENFIGI_API_KEY': {
                'base_url': 'https://api.openfigi.com/v3',
                'doc_url': 'https://www.openfigi.com/api',
                'auth_type': 'Bearer',
                'rate_limits': {'requests_per_day': 250},  # Free tier
                'tier': 'free'
            },
            'BRAVE_SEARCH_API_KEY': {
                'base_url': 'https://api.search.brave.com/res/v1',
                'doc_url': 'https://api.search.brave.com/app/docs',
                'auth_type': 'Bearer',
                'rate_limits': {'requests_per_month': 1000},  # Free tier
                'tier': 'free'
            },
            'EXA_AI_API_KEY': {
                'base_url': 'https://api.exa.ai/v1',
                'doc_url': 'https://docs.exa.ai',
                'auth_type': 'Bearer',
                'rate_limits': {'requests_per_month': 1000},  # Free tier
                'tier': 'free'
            },
            'APITUBE_API_KEY': {
                'base_url': 'https://api.apitube.io/v1',
                'doc_url': 'https://docs.apitube.io',
                'auth_type': 'Bearer',
                'rate_limits': {'requests_per_day': 100},  # Free tier
                'tier': 'free'
            },
            'FINANCIAL_MODELING_PREP_API_KEY': {
                'base_url': 'https://financialmodelingprep.com/api/v3',
                'doc_url': 'https://site.financialmodelingprep.com/developer/docs',
                'auth_type': 'Bearer',
                'rate_limits': {'requests_per_day': 250},  # Free tier
                'tier': 'free'
            },
            'POLYGON_API_KEY': {
                'base_url': 'https://api.polygon.io/v3',
                'doc_url': 'https://polygon.io/docs',
                'auth_type': 'Bearer',
                'rate_limits': {
                    'requests_per_minute': 5,  # Free tier
                    'requests_per_day': 1000
                },
                'tier': 'free'
            },
            'SCRAPING_NINJA_API_KEY': {
                'base_url': 'https://scrapeninja.p.rapidapi.com',
                'doc_url': 'https://rapidapi.com/restyler/api/scrapeninja',
                'auth_type': 'RapidAPI',
                'rate_limits': {
                    'js_requests_per_month': 50,    # JavaScript-enabled requests
                    'basic_requests_per_month': 500  # Regular requests
                },
                'tier': 'basic'
            }
        }
        
        # Track API usage across runs
        self.usage_tracking = {}
        
    async def track_usage(self, api_name: str, count: int = 1):
        """Track API usage and check limits if known
        
        Args:
            api_name: Name of the API being used
            count: Number of requests/tokens to add
        
        Returns:
            bool: Whether the request should proceed
        """
        now = datetime.now()
        if api_name not in self.usage_tracking:
            self.usage_tracking[api_name] = {
                'daily': {'count': 0, 'reset': now},
                'monthly': {'count': 0, 'reset': now},
                'minute': {'count': 0, 'reset': now}
            }
        
        tracking = self.usage_tracking[api_name]
        limits = self.api_configs[api_name]['rate_limits']
        
        # If limits unknown, just track usage without enforcing
        if limits == 'unknown':
            tracking['daily']['count'] += count
            tracking['monthly']['count'] += count
            tracking['minute']['count'] += count
            return True
        
        # Reset counters if needed
        if now - tracking['daily']['reset'] > timedelta(days=1):
            tracking['daily'] = {'count': 0, 'reset': now}
        if now - tracking['monthly']['reset'] > timedelta(days=30):
            tracking['monthly'] = {'count': 0, 'reset': now}
        if now - tracking['minute']['reset'] > timedelta(minutes=1):
            tracking['minute'] = {'count': 0, 'reset': now}
        
        # Check limits
        if 'requests_per_day' in limits:
            if tracking['daily']['count'] + count > limits['requests_per_day']:
                self.logger.warning(f"{api_name} daily limit reached")
                return False
                
        if 'requests_per_month' in limits:
            if tracking['monthly']['count'] + count > limits['requests_per_month']:
                self.logger.warning(f"{api_name} monthly limit reached")
                return False
                
        if 'requests_per_minute' in limits:
            if tracking['minute']['count'] + count > limits['requests_per_minute']:
                self.logger.warning(f"{api_name} rate limit reached")
                return False
        
        # Update counters
        tracking['daily']['count'] += count
        tracking['monthly']['count'] += count
        tracking['minute']['count'] += count
        
        return True

    def get_usage_stats(self) -> Dict[str, Dict]:
        """Get current usage statistics for all APIs"""
        stats = {}
        for api_name, tracking in self.usage_tracking.items():
            limits = self.api_configs[api_name]['rate_limits']
            stats[api_name] = {
                'usage': {
                    'daily': tracking['daily']['count'],
                    'monthly': tracking['monthly']['count'],
                    'minute': tracking['minute']['count']
                },
                'limits': limits,
                'tier': self.api_configs[api_name]['tier']
            }
        return stats

    async def process(self) -> Dict[str, APIDocumentation]:
        """Main processing method - orchestrates the documentation retrieval
        
        Returns:
            Dict mapping API names to their documentation
        """
        self.logger.info("Starting API documentation retrieval")
        docs = await self.fetch_all_documentation()
        self.logger.info(f"Retrieved documentation for {len(docs)} APIs")
        return docs

    async def analyze_api_docs(self, api_name: str) -> Dict:
        """Use DeepSeek to analyze API documentation and extract available data types
        
        Prompts DeepSeek to:
        1. Fetch and read the API documentation
        2. Extract rate limits and tier information
        3. Analyze what types of data are available
        4. Structure the data consistently
        
        Args:
            api_name: Name of API to analyze
            
        Returns:
            Dict containing rate limits, tier info, and data types
        """
        config = self.api_configs[api_name]
        prompt = f"""
        Analyze the documentation at {config['doc_url']} for {api_name}.
        Extract the following information:
        - Rate limits (requests per second/minute/day/month)
        - Tier information (free, paid, enterprise)
        - Any usage quotas or limitations
        - Types of data available through the API
        - Data formats and fields provided
        
        Format the response as JSON with:
        {{
            "rate_limits": {{
                "requests_per_second": number or null,
                "requests_per_minute": number or null,
                "requests_per_day": number or null,
                "requests_per_month": number or null
            }},
            "tier": "free|paid|enterprise",
            "quotas": {{
                "description": "text description of any quotas",
                "limits": ["list", "of", "quota", "details"]
            }},
            "data_types": {{
                "categories": ["list", "of", "data", "categories"],
                "fields": ["list", "of", "available", "fields"],
                "formats": ["json", "csv", "etc"],
                "special_features": ["any", "special", "data", "features"]
            }},
            "commercial_usage": {{
                "allowed": boolean,
                "attribution_required": boolean
            }}
        }}
        """
        
        try:
            response = await self.llm.complete(prompt)
            analysis = json.loads(response)
            
            # Ensure all required fields are present with defaults if missing
            analysis = {
                "rate_limits": analysis.get("rate_limits", {}),
                "tier": analysis.get("tier", "unknown"),
                "quotas": analysis.get("quotas", {
                    "description": "Unknown",
                    "limits": []
                }),
                "data_types": analysis.get("data_types", {
                    "categories": [],
                    "fields": [],
                    "formats": [],
                    "special_features": []
                }),
                "commercial_usage": analysis.get("commercial_usage", {
                    "allowed": True,
                    "attribution_required": True
                })
            }
            
            # Update the config with the analysis results
            self.api_configs[api_name].update(analysis)
            
            self.logger.info(f"Successfully analyzed docs for {api_name}")
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing docs for {api_name}: {e}")
            return {
                "rate_limits": {},
                "tier": "unknown",
                "quotas": {"description": "Could not determine", "limits": []},
                "data_types": {
                    "categories": [],
                    "fields": [],
                    "formats": [],
                    "special_features": []
                },
                "commercial_usage": {
                    "allowed": True,
                    "attribution_required": True
                }
            }

    async def get_commercial_usage_status(self, api_name: str) -> Dict:
        """Get data types and basic commercial usage info for an API
        
        Returns information about:
        - Types of data available
        - Data formats and fields
        - Basic commercial usage flags
        
        Args:
            api_name: Name of the API to check
            
        Returns:
            Dict containing data types and usage details
        """
        if api_name not in self.api_configs:
            return None
            
        config = self.api_configs[api_name]
        
        # Get the simulated data from the LLM client
        prompt = f"""
        Analyze the documentation at {config['doc_url']} for {api_name}.
        Extract data types and commercial usage information.
        """
        try:
            response = json.loads(await self.llm.complete(prompt))
            if isinstance(response, dict) and 'data_types' in response:
                return {
                    "name": api_name,
                    "data_types": response['data_types'],
                    "commercial_usage": response['commercial_usage'],
                    "tier": response.get('tier', config.get('tier', 'unknown'))
                }
        except:
            pass
            
        return {
            "name": api_name,
            "data_types": config.get("data_types", {
                "categories": [],
                "fields": [],
                "formats": [],
                "special_features": []
            }),
            "commercial_usage": config.get("commercial_usage", {
                "allowed": True,
                "attribution_required": True
            }),
            "tier": config.get("tier", "unknown")
        }

    async def _fetch_documentation(self, api_name: str, config: Dict) -> Optional[APIDocumentation]:
        """Fetch API documentation for a specific API
        
        Args:
            api_name: Name of the API
            config: Configuration for the API
            
        Returns:
            APIDocumentation object if successful, None otherwise
        """
        try:
            # Create basic documentation object
            doc = APIDocumentation(
                name=api_name,
                base_url=config['base_url'],
                auth_type=config['auth_type'],
                endpoints=[],  # We'll populate this later if needed
                rate_limits=config.get('rate_limits', {}),
                version=None,
                data_types=config.get('data_types', {
                    'categories': [],
                    'fields': [],
                    'formats': [],
                    'special_features': []
                }),
                commercial_usage=config.get('commercial_usage', {
                    'allowed': True,
                    'attribution_required': True
                })
            )
            
            # If we have simulated data in the config, use it
            if 'data_types' in config:
                doc.data_types = config['data_types']
            if 'commercial_usage' in config:
                doc.commercial_usage = config['commercial_usage']
            if 'rate_limits' in config:
                doc.rate_limits = config['rate_limits']
            
            return doc
        except Exception as e:
            self.logger.error(f"Error creating documentation for {api_name}: {e}")
            return None

    async def fetch_all_documentation(self):
        """Fetch and analyze documentation for all APIs"""
        docs = {}
        for api_name in self.api_configs:
            try:
                # First analyze the docs with DeepSeek
                analysis = await self.analyze_api_docs(api_name)
                if analysis:
                    # Update the config with the analysis results
                    self.api_configs[api_name].update({
                        'data_types': analysis.get('data_types', {
                            'categories': [],
                            'fields': [],
                            'formats': [],
                            'special_features': []
                        }),
                        'commercial_usage': analysis.get('commercial_usage', {
                            'allowed': True,
                            'attribution_required': True
                        }),
                        'tier': analysis.get('tier', 'unknown'),
                        'rate_limits': analysis.get('rate_limits', {})
                    })
                
                # Then create the documentation object with the updated config
                doc = await self._fetch_documentation(api_name, self.api_configs[api_name])
                if doc:
                    # Ensure the doc has the latest data
                    doc.data_types = self.api_configs[api_name].get('data_types', {})
                    doc.commercial_usage = self.api_configs[api_name].get('commercial_usage', {})
                    doc.rate_limits = self.api_configs[api_name].get('rate_limits', {})
                    docs[api_name] = doc
            except Exception as e:
                self.logger.error(f"Error processing {api_name}: {e}")
                
        return docs

    def generate_markdown(self, docs: Dict[str, APIDocumentation]) -> str:
        """Generates formatted markdown documentation
        
        Creates a structured markdown document with:
        - API overview sections
        - Authentication details
        - Rate limit information
        - Detailed endpoint documentation
        
        Args:
            docs: Dict mapping API names to their documentation
            
        Returns:
            Formatted markdown string
        """
        md = "# API Documentation\n\n"
        
        for api_name, doc in docs.items():
            # API Overview section
            md += f"## {api_name}\n\n"
            md += f"Base URL: `{doc.base_url}`\n"
            md += f"Authentication: {doc.auth_type}\n"
            
            # Rate Limits section
            if doc.rate_limits:
                md += "**Rate Limits:**\n"
                for limit_type, value in doc.rate_limits.items():
                    md += f"- {limit_type}: {value}\n"
            
            # Version info if available
            if doc.version:
                md += f"Version: {doc.version}\n"
            
            # Detailed endpoint documentation
            md += "\n### Endpoints\n\n"
            for endpoint in doc.endpoints:
                md += f"#### {endpoint.method} {endpoint.path}\n"
                md += f"{endpoint.description}\n\n"
                
                if endpoint.parameters:
                    md += "**Parameters:**\n\n"
                    for param in endpoint.parameters:
                        md += f"- `{param['name']}`: {param['description']}\n"
                md += "\n"
                
        return md

    async def save_documentation(self, output_path: str = "API_DOCUMENTATION.md"):
        """Processes and saves API documentation to file
        
        Complete workflow:
        1. Fetches all API documentation
        2. Generates formatted markdown
        3. Saves to specified file
        
        Args:
            output_path: Where to save the markdown file
        """
        docs = await self.process()
        markdown = self.generate_markdown(docs)
        
        with open(output_path, 'w') as f:
            f.write(markdown)
        
        self.logger.info(f"Saved API documentation to {output_path}")

    async def discover_violation_databases(self) -> Dict:
        """Use DeepSeek to discover violation tracking and misconduct databases"""
        prompt = """
        Find and analyze corporate violation and misconduct tracking databases like violationtracker.goodjobsfirst.org.
        Focus on databases that track:
        - Regulatory violations and fines
        - Corporate misconduct records
        - Settlement and penalty data
        - Environmental violations
        - Labor law violations
        - Safety violations
        - Financial misconduct
        
        Format as JSON with structure:
        {
            "databases": [
                {
                    "name": "Database name",
                    "url": "Homepage URL",
                    "description": "What violations/misconduct it tracks",
                    "data_coverage": {
                        "historical_range": "e.g. 1990-present",
                        "update_frequency": "how often updated",
                        "geographical": ["covered", "regions"]
                    },
                    "violation_types": ["types", "of", "violations", "tracked"],
                    "data_fields": ["specific", "fields", "available"],
                    "access_methods": ["api", "bulk_download", "web_interface"],
                    "data_quality": {
                        "verification": "how violations are verified",
                        "source_citations": true,
                        "standardization": "how data is standardized"
                    },
                    "pricing": "Any pricing info"
                }
            ]
        }
        """
        try:
            response = await self.llm.complete(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error discovering violation databases: {e}")
            return {"databases": []}

    async def discover_regulatory_sources(self) -> Dict:
        """Use DeepSeek to discover regulatory and compliance data sources"""
        prompt = """
        Find and analyze regulatory and compliance data sources. Focus on:
        - Government regulatory databases
        - SEC filings beyond standard EDGAR
        - International regulatory bodies
        - Industry-specific regulators
        - Compliance monitoring systems
        - Enforcement action databases
        
        Format as JSON with structure:
        {
            "sources": [
                {
                    "name": "Source name",
                    "url": "Homepage URL",
                    "description": "What regulatory data it provides",
                    "coverage": {
                        "jurisdictions": ["list", "of", "jurisdictions"],
                        "industries": ["covered", "industries"],
                        "update_frequency": "how often updated"
                    },
                    "data_types": ["types", "of", "regulatory", "data"],
                    "access_methods": ["how", "to", "access", "data"],
                    "data_quality": {
                        "official_status": "government/private/etc",
                        "verification": "verification process",
                        "standardization": "data standards used"
                    },
                    "access_requirements": "Any special access needs"
                }
            ]
        }
        """
        try:
            response = await self.llm.complete(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error discovering regulatory sources: {e}")
            return {"sources": []}

    async def discover_alternative_data(self) -> Dict:
        """Use DeepSeek to discover alternative data sources"""
        prompt = """
        Find and analyze alternative data sources for corporate research. Focus on:
        - Political contribution and lobbying databases
        - Government contract databases
        - Subsidy tracking systems
        - Supply chain relationship data
        - Executive compensation databases
        - Corporate structure/ownership databases
        - ESG incident trackers
        
        Format as JSON with structure:
        {
            "sources": [
                {
                    "name": "Source name",
                    "url": "Homepage URL",
                    "description": "What alternative data it provides",
                    "unique_value": ["what", "makes", "it", "valuable"],
                    "data_types": {
                        "categories": ["main", "data", "categories"],
                        "fields": ["specific", "fields", "available"]
                    },
                    "coverage": {
                        "temporal": "time coverage",
                        "scope": ["what", "is", "covered"],
                        "frequency": "update frequency"
                    },
                    "access_methods": ["how", "to", "get", "data"],
                    "pricing": "Cost information"
                }
            ]
        }
        """
        try:
            response = await self.llm.complete(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error discovering alternative data: {e}")
            return {"sources": []}

    async def discover_all_sources(self) -> Dict:
        """Run all discovery methods and combine results"""
        violations = await self.discover_violation_databases()
        regulatory = await self.discover_regulatory_sources()
        alternative = await self.discover_alternative_data()
        
        return {
            "violation_databases": violations["databases"],
            "regulatory_sources": regulatory["sources"],
            "alternative_data": alternative["sources"]
        }

    async def is_js_required(self, url: str) -> bool:
        """
        Determines if a URL likely requires JavaScript for proper rendering
        
        Args:
            url: The URL to analyze
            
        Returns:
            bool: True if JavaScript is likely required
        """
        # Common patterns that suggest JavaScript is needed
        js_indicators = [
            'docs.api.',
            'swagger.',
            'redoc.',
            'developer.', 
            'documentation.',
            'apidocs.',
            'rapidapi.com'
        ]
        
        # Sites known to work without JS
        static_sites = [
            'raw.githubusercontent.com',
            'api.github.com',
            'gitlab.com/api',
            'bitbucket.org/api'
        ]
        
        url_lower = url.lower()
        
        # Check if it's a known static site
        if any(site in url_lower for site in static_sites):
            return False
        
        # Check for JS indicators
        return any(indicator in url_lower for indicator in js_indicators)

    async def get_scraping_quota(self) -> Dict[str, int]:
        """
        Get remaining scraping quota for the month
        
        Returns:
            Dict with remaining js and basic requests
        """
        tracking = self.usage_tracking.get('SCRAPING_NINJA_API_KEY', {})
        monthly = tracking.get('monthly', {'count': 0, 'js_count': 0})
        
        limits = self.api_configs['SCRAPING_NINJA_API_KEY']['rate_limits']
        
        return {
            'js_remaining': limits['js_requests_per_month'] - monthly.get('js_count', 0),
            'basic_remaining': limits['basic_requests_per_month'] - monthly.get('count', 0)
        }

    async def scrape_api_documentation(self, url: str) -> Dict:
        """
        Scrapes API documentation from a given URL using ScrapingNinja
        
        Args:
            url: The URL of the API documentation to scrape
            
        Returns:
            Dict containing the scraped documentation structure
        """
        # Check quotas
        quota = await self.get_scraping_quota()
        needs_js = await self.is_js_required(url)
        
        if needs_js and quota['js_remaining'] <= 0:
            self.logger.warning(f"No JS-enabled scraping quota remaining for {url}")
            return None
        elif not needs_js and quota['basic_remaining'] <= 0:
            self.logger.warning(f"No basic scraping quota remaining for {url}")
            return None
        
        headers = {
            'Content-Type': 'application/json',
            'x-rapidapi-host': 'scrapeninja.p.rapidapi.com',
            'x-rapidapi-key': os.getenv('SCRAPING_NINJA_API_KEY')
        }
        
        payload = {
            "url": url,
            "js": needs_js,  # Enable JS only when needed
            "timeout": 20000 if needs_js else 10000  # Longer timeout for JS
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://scrapeninja.p.rapidapi.com/scrape',
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Update usage tracking
                        if not 'SCRAPING_NINJA_API_KEY' in self.usage_tracking:
                            self.usage_tracking['SCRAPING_NINJA_API_KEY'] = {
                                'monthly': {'count': 0, 'js_count': 0, 'reset': datetime.now()}
                            }
                        
                        tracking = self.usage_tracking['SCRAPING_NINJA_API_KEY']['monthly']
                        if needs_js:
                            tracking['js_count'] += 1
                        else:
                            tracking['count'] += 1
                        
                        # Process the scraped content through LLM
                        prompt = f"""
                        Analyze this API documentation and extract:
                        - Endpoints and their descriptions
                        - Authentication methods
                        - Rate limits
                        - Data types and response formats
                        
                        Raw content:
                        {data.get('body', '')}
                        
                        Format as JSON with structure:
                        {{
                            "endpoints": [
                                {{
                                    "path": "/path",
                                    "method": "GET/POST/etc",
                                    "description": "what it does",
                                    "parameters": [
                                        {{
                                            "name": "param name",
                                            "description": "param description"
                                        }}
                                    ]
                                }}
                            ],
                            "auth_methods": ["list", "of", "methods"],
                            "rate_limits": {{
                                "requests_per_second": number,
                                "requests_per_day": number
                            }},
                            "data_types": ["supported", "data", "types"]
                        }}
                        """
                        
                        structured_docs = await self.llm.complete(prompt)
                        return json.loads(structured_docs)
                    else:
                        self.logger.error(f"Failed to scrape {url}: {response.status}")
                        return None
                    
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return None

    async def bulk_scrape_documentation(self, urls: List[str]) -> Dict[str, Dict]:
        """
        Scrapes multiple API documentation URLs in parallel, respecting quota limits
        
        Args:
            urls: List of documentation URLs to scrape
            
        Returns:
            Dict mapping URLs to their structured documentation
        """
        # Check quotas and categorize URLs
        quota = await self.get_scraping_quota()
        js_urls = []
        basic_urls = []
        
        for url in urls:
            if await self.is_js_required(url):
                if quota['js_remaining'] > 0:
                    js_urls.append(url)
                    quota['js_remaining'] -= 1
                else:
                    self.logger.warning(f"Skipping {url} - no JS quota remaining")
            else:
                if quota['basic_remaining'] > 0:
                    basic_urls.append(url)
                    quota['basic_remaining'] -= 1
                else:
                    self.logger.warning(f"Skipping {url} - no basic quota remaining")
        
        # Scrape in parallel, but with a small delay between requests
        async def _scrape_single(url: str, delay: float) -> Tuple[str, Dict]:
            await asyncio.sleep(delay)  # Avoid hitting rate limits
            result = await self.scrape_api_documentation(url)
            return (url, result)
        
        # Process JS-enabled requests first (they're more quota-limited)
        js_tasks = [_scrape_single(url, i * 0.5) for i, url in enumerate(js_urls)]
        basic_tasks = [_scrape_single(url, i * 0.2) for i, url in enumerate(basic_urls)]
        
        all_results = await asyncio.gather(*(js_tasks + basic_tasks))
        return {url: doc for url, doc in all_results if doc is not None}

# Example usage
async def main():
    """Entry point for documentation generation"""
    engine = APIDocEngine()
    await engine.save_documentation()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
