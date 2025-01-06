from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os
from dotenv import load_dotenv
from duckduckgo_search import DDGS
import requests
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from tqdm import tqdm
import time
from ratelimit import limits, sleep_and_retry
from functools import wraps
from urllib.parse import urlparse
import hashlib

from db import get_connection, insert_company

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('research_workflow.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Environment setup
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# Rate limiting configuration
DEEPSEEK_CALLS_PER_MINUTE = 25  # More conservative API limit
SEARCH_CALLS_PER_MINUTE = 15    # More conservative DuckDuckGo rate limit
DELAY_BETWEEN_SEARCHES = 2      # Seconds between search calls

# Add these constants at the top with other configurations
CHECKPOINT_STAGES = {
    'CONTEXT': 1,
    'QUERIES': 2,
    'SEARCH': 3,
    'SUMMARY': 4,
    'STRUCTURED': 5,
    'COMPLETE': 6
}

def rate_limit_decorator(calls_per_minute):
    """Generic rate limit decorator"""
    def decorator(func):
        @sleep_and_retry
        @limits(calls=calls_per_minute, period=60)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def count_tokens(text: str) -> int:
    """Estimate token count using a simple approximation"""
    # Simple approximation: 1 token ≈ 4 characters for English text
    return len(text) // 4

@rate_limit_decorator(DEEPSEEK_CALLS_PER_MINUTE)
def call_deepseek_api(messages: List[Dict], temperature: float = 0.2) -> Dict:
    """Rate-limited DeepSeek API call with token tracking"""
    try:
        if not DEEPSEEK_API_KEY:
            logging.error("DeepSeek API key is not set")
            return None
            
        # Count input tokens
        input_text = " ".join(msg["content"] for msg in messages)
        input_tokens = count_tokens(input_text)
        logging.info(f"Input tokens: {input_tokens}")
            
        logging.info(f"Making DeepSeek API call with temperature {temperature}")
        response = requests.post(
            API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000
            },
            timeout=30
        )
        
        if response.status_code == 401:
            logging.error("DeepSeek API authentication failed. Check your API key.")
            return None
        elif response.status_code == 429:
            logging.error("DeepSeek API rate limit exceeded")
            return None
        elif response.status_code != 200:
            logging.error(f"DeepSeek API error: Status {response.status_code}, Response: {response.text}")
            return None
            
        try:
            response_json = response.json()
            
            # Count output tokens
            if "choices" in response_json and response_json["choices"]:
                output_text = response_json["choices"][0]["message"]["content"]
                output_tokens = count_tokens(output_text)
                total_tokens = input_tokens + output_tokens
                logging.info(f"Output tokens: {output_tokens}, Total tokens: {total_tokens}")
                
                # Add token counts to response
                response_json["token_usage"] = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                }
            
        except json.JSONDecodeError:
            logging.error(f"Failed to parse DeepSeek API response: {response.text}")
            return None
            
        if "choices" not in response_json or not response_json["choices"]:
            logging.error(f"Unexpected API response format: {response_json}")
            return None
            
        if "message" not in response_json["choices"][0]:
            logging.error(f"No message in API response: {response_json}")
            return None
            
        logging.info("Successfully received API response")
        return response_json
        
    except requests.exceptions.Timeout:
        logging.error("DeepSeek API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"DeepSeek API request failed: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error in DeepSeek API call: {str(e)}")
        return None

class RateLimitedDDGS:
    """Rate-limited wrapper for DuckDuckGo search"""
    def __init__(self, timeout: int = 10, proxies: Optional[str] = None):
        self.ddgs = DDGS(timeout=timeout)
        self.last_call_time = 0

    def _wait_for_rate_limit(self):
        """Ensure minimum delay between calls"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < DELAY_BETWEEN_SEARCHES:
            time.sleep(DELAY_BETWEEN_SEARCHES - time_since_last_call)
        self.last_call_time = time.time()

    @rate_limit_decorator(SEARCH_CALLS_PER_MINUTE)
    def search(self, keywords: str, **kwargs) -> List[Dict]:
        """Rate-limited search"""
        self._wait_for_rate_limit()
        return list(self.ddgs.text(keywords=keywords, **kwargs))

    @rate_limit_decorator(SEARCH_CALLS_PER_MINUTE)
    def news_search(self, keywords: str, **kwargs) -> List[Dict]:
        """Rate-limited news search"""
        self._wait_for_rate_limit()
        return list(self.ddgs.news(keywords=keywords, **kwargs))

@dataclass
class SearchConfig:
    """Configuration for a search strategy"""
    category: str  # environmental_safety, financial_legal, or ethical_social
    query: str
    sources: List[str]
    date_range: Optional[str] = None
    keywords: List[str] = None

def is_investment_product(name: str, ticker: str, description: str = None) -> Dict[str, any]:
    """
    Identify if a company is actually an investment product (ETF, mutual fund, etc.)
    Returns a dict with classification and confidence
    """
    # Common identifiers in names/tickers
    fund_indicators = [
        ' ETF', ' Fund', ' Trust', 'iShares', 'Vanguard', 'SPDR', 
        ' Capital Allocation', ' Income ', 'Index',
        'Sustainable', 'ESG', ' PRE', ' PRF', ' PR', ' PFD',
        'Preferred', 'Pref', 'Alger', 'BlackRock', 'PIMCO',
        'American Century', ' - ', 'Ecofin'
    ]
    
    # Ticker patterns typical of funds/investment products
    ticker_patterns = [
        'PR[A-Z]',  # Preferred shares
        '[A-Z]{4}X',  # Many mutual funds end in X
        '^BX[A-Z]',   # BlackRock funds
        '^IV[A-Z]',   # Investment vehicles
        '^ET[A-Z]'    # ETF-related
    ]
    
    matches = []
    confidence = 0
    
    # Check name indicators
    for indicator in fund_indicators:
        if indicator.lower() in name.lower():
            matches.append(f"Name contains '{indicator}'")
            confidence += 25
    
    # Check ticker patterns
    import re
    for pattern in ticker_patterns:
        if re.search(pattern, ticker):
            matches.append(f"Ticker matches pattern '{pattern}'")
            confidence += 25
    
    # Check description if available
    if description:
        fund_terms = ['fund', 'etf', 'investment trust', 'investment company', 
                     'mutual fund', 'index fund', 'exchange traded']
        for term in fund_terms:
            if term.lower() in description.lower():
                matches.append(f"Description contains '{term}'")
                confidence += 20

    # Cap confidence at 100
    confidence = min(confidence, 100)
    
    return {
        'is_investment_product': confidence >= 50,
        'confidence': confidence,
        'matches': matches,
        'type': 'investment_product' if confidence >= 50 else 'operating_company'
    }

def get_top_companies(limit: int = 150) -> List[Dict]:
    """Get top companies by tick score, excluding investment products"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, ticker, tick, description 
            FROM companies 
            WHERE tick IS NOT NULL 
            ORDER BY tick DESC
        """)
        
        companies = []
        investment_products = []
        
        for row in cursor.fetchall():
            company = {
                'name': row[0],
                'ticker': row[1],
                'tick': row[2],
                'description': row[3]
            }
            
            # Classify the company
            classification = is_investment_product(
                company['name'], 
                company['ticker'], 
                company['description']
            )
            
            if classification['is_investment_product']:
                investment_products.append({
                    **company,
                    **classification
                })
            else:
                companies.append(company)
                
            if len(companies) >= limit:
                break
        
        # Log investment products for review
        logging.info(f"Found {len(investment_products)} investment products:")
        for product in investment_products:
            logging.info(f"Investment Product: {product['name']} ({product['ticker']}) - "
                        f"Confidence: {product['confidence']}% - "
                        f"Matches: {', '.join(product['matches'])}")
        
        return companies

def generate_summary(company_results: Dict, company_name: str, company_context: str = None) -> str:
    """Generate a comprehensive summary of research findings"""
    try:
        context = f"Research summary for {company_name}:\n\n"
        if company_context:
            context += f"Company Context:\n{company_context}\n\n"
            
        for category in company_results:
            context += f"\n{category['category'].upper()} FINDINGS:\n"
            for result_type in ['web_results', 'news_results']:
                for result in category[result_type][:3]:
                    context += f"- {result['title']}: {result['snippet']}\n"

        messages = [
            {"role": "system", "content": """You are a research analyst. Synthesize the provided information 
             into a concise summary highlighting key risks, controversies, and notable findings. Focus on 
             material issues that could impact investment decisions."""},
            {"role": "user", "content": context}
        ]
        
        response = call_deepseek_api(messages, temperature=0.3)
        if response:
            return response["choices"][0]["message"]["content"]
        else:
            logging.error("Error generating summary: API call failed")
            return "Error generating summary"
            
    except Exception as e:
        logging.error(f"Error in summary generation: {str(e)}")
        return f"Error generating summary: {str(e)}"

def extract_structured_data(company_results: Dict, summary: str, company_name: str) -> Dict:
    """Extract structured data points from research results"""
    try:
        # Create a simpler context with key information
        context = f"""Company: {company_name}

Summary of findings:
{summary}

Analyze the above information and provide a structured assessment in this exact JSON format:
{{
    "risk_score": 50,  // Score from 0-100, where 100 is highest risk
    "key_risks": [
        "Example risk 1",
        "Example risk 2"
    ],
    "controversies": [
        "Example controversy 1",
        "Example controversy 2"
    ],
    "environmental_issues": [
        "Example environmental issue"
    ],
    "social_issues": [
        "Example social issue"
    ],
    "governance_issues": [
        "Example governance issue"
    ],
    "recommendation": "caution",  // Must be one of: "avoid", "caution", or "clear"
    "confidence_score": 75  // Score from 0-100 indicating confidence in assessment
}}"""

        messages = [
            {"role": "system", "content": """You are a risk assessment analyst. 
            Analyze the provided information and respond with a JSON object exactly matching the specified format.
            Remove any comments from the JSON before responding."""},
            {"role": "user", "content": context}
        ]
        
        logging.info(f"Extracting structured data for {company_name}")
        response = call_deepseek_api(messages, temperature=0.2)
        
        if not response or "choices" not in response:
            logging.error("No valid response from API for structured data extraction")
            return {}
            
        try:
            content = response["choices"][0]["message"]["content"].strip()
            
            # Try to find JSON object in the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                logging.error(f"No JSON object found in response: {content}")
                return {}
                
            content = json_match.group()
            # Remove any remaining comments
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            
            data = json.loads(content)
            
            # Validate the structure
            required_fields = [
                'risk_score', 'key_risks', 'controversies', 
                'environmental_issues', 'social_issues', 'governance_issues',
                'recommendation', 'confidence_score'
            ]
            
            if not all(field in data for field in required_fields):
                logging.error(f"Missing required fields in structured data: {data}")
                return {}
                
            # Validate data types
            if not isinstance(data['risk_score'], (int, float)):
                data['risk_score'] = 50
            if not isinstance(data['confidence_score'], (int, float)):
                data['confidence_score'] = 50
                
            # Ensure scores are in valid range
            data['risk_score'] = max(0, min(100, data['risk_score']))
            data['confidence_score'] = max(0, min(100, data['confidence_score']))
            
            # Validate recommendation
            valid_recommendations = ['avoid', 'caution', 'clear']
            if data['recommendation'] not in valid_recommendations:
                data['recommendation'] = 'caution'
                
            # Ensure all lists are present
            for field in ['key_risks', 'controversies', 'environmental_issues', 'social_issues', 'governance_issues']:
                if not isinstance(data[field], list):
                    data[field] = []
                    
            logging.info(f"Successfully extracted structured data for {company_name}")
            return data
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse structured data response: {str(e)}\nContent: {content}")
            return {}
        except Exception as e:
            logging.error(f"Error processing structured data response: {str(e)}")
            return {}
            
    except Exception as e:
        logging.error(f"Error in structured data extraction: {str(e)}")
        return {}

@dataclass
class Source:
    """Structured representation of a source with metadata"""
    url: str
    title: str
    snippet: str
    domain: str
    source_type: str  # 'web' or 'news'
    category: str  # 'environmental_safety', 'financial_legal', or 'ethical_social'
    query_context: str
    retrieved_at: str
    published_date: Optional[str] = None
    source_hash: Optional[str] = None
    
    def __post_init__(self):
        # Parse domain from URL
        parsed_url = urlparse(self.url)
        self.domain = parsed_url.netloc
        
        # Generate unique hash for deduplication
        self.source_hash = hashlib.md5(
            f"{self.url}{self.title}{self.snippet}".encode()
        ).hexdigest()

def get_company_context(company_name: str, ticker: str) -> Union[str, Dict]:
    """Generate initial company context using DeepSeek"""
    try:
        # Skip companies with non-English characters or known foreign indicators
        if any(ord(c) > 127 for c in company_name) or \
           any(x in company_name.lower() for x in ['sa', 'sab', 'ab', 'ag', 'nv', 'asa', 'oyj', 'plc', 'se']):
            logging.info(f"Skipping non-English company: {company_name}")
            return "Non-English company"

        context_prompt = f"""Generate a comprehensive overview of {company_name} ({ticker}).
        Focus on:
        1. Core business activities and industry
        2. Major products or services
        3. Geographic presence and scale
        4. Key business relationships and dependencies
        5. Recent major developments or changes
        6. Known areas of concern or controversy
        
        Format the response as a structured overview that can be used to inform further research."""

        messages = [
            {"role": "system", "content": "You are a business analyst providing company overviews."},
            {"role": "user", "content": context_prompt}
        ]
        
        response = call_deepseek_api(messages, temperature=0.3)
        if response and isinstance(response, dict) and "choices" in response:
            return response
        else:
            logging.error(f"Failed to generate context for {company_name}")
            return "Error generating company context"
            
    except Exception as e:
        logging.error(f"Error in context generation: {str(e)}")
        return "Error generating company context"

def generate_search_queries(company_name: str, company_context: str) -> Union[List[Dict], Dict]:
    """Generate diverse search queries based on company context"""
    try:
        if not company_name:
            logging.error("Company name is required")
            return []
            
        if not company_context or company_context in ["Error generating company context", "Non-English company"]:
            logging.error("Invalid company context")
            return []
            
        # Create a simpler, more direct prompt
        query_prompt = f"""Based on this company context:
{company_context}

Generate 3 search queries to investigate risks and controversies for {company_name}.
Format your response as a JSON array like this example:
[
    {{
        "category": "environmental_safety",
        "query": "{company_name} environmental violations",
        "rationale": "Check for environmental compliance history",
        "priority": 1
    }}
]

Use only these categories: environmental_safety, financial_legal, ethical_social"""

        messages = [
            {"role": "system", "content": "You are a research analyst. Respond only with a properly formatted JSON array."},
            {"role": "user", "content": query_prompt}
        ]
        
        logging.info("Generating search queries...")
        response = call_deepseek_api(messages, temperature=0.2)
        
        if response and isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"].strip()
            try:
                # Try to parse the JSON response
                queries = json.loads(content)
                if isinstance(queries, list) and len(queries) > 0:
                    return response
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON response for {company_name}")
                return []
        
        logging.error(f"Failed to generate queries for {company_name}")
        return []
            
    except Exception as e:
        logging.error(f"Error in query generation: {str(e)}")
        return []

class ResearchWorkflow:
    def __init__(self, timeout: int = 10, proxies: Optional[str] = None):
        self.search_utils = RateLimitedDDGS(timeout=timeout)
        self._ensure_checkpoint_table()
    
    def _ensure_checkpoint_table(self):
        """Ensure checkpoint table exists"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_checkpoints (
                    company_ticker TEXT PRIMARY KEY,
                    stage INTEGER NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    partial_results JSON,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            # Create research_sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_ticker TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    snippet TEXT,
                    domain TEXT,
                    source_type TEXT,
                    category TEXT,
                    query_context TEXT,
                    retrieved_at TEXT,
                    published_date TEXT,
                    UNIQUE(company_ticker, source_hash)
                )
            """)
            conn.commit()
    
    def _get_checkpoint(self, ticker: str) -> Optional[Dict]:
        """Get the current checkpoint for a company"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stage, partial_results, retry_count
                FROM research_checkpoints
                WHERE company_ticker = ?
            """, (ticker,))
            row = cursor.fetchone()
            if row:
                return {
                    'stage': row[0],
                    'partial_results': json.loads(row[1]) if row[1] else {},
                    'retry_count': row[2]
                }
            return None
    
    def _update_checkpoint(self, ticker: str, stage: int, partial_results: Dict = None, error: str = None):
        """Update checkpoint for a company"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO research_checkpoints 
                (company_ticker, stage, partial_results, error_message, last_updated)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (company_ticker) DO UPDATE SET
                stage = excluded.stage,
                partial_results = excluded.partial_results,
                error_message = excluded.error_message,
                last_updated = CURRENT_TIMESTAMP,
                retry_count = CASE 
                    WHEN excluded.stage <= research_checkpoints.stage 
                    THEN research_checkpoints.retry_count + 1
                    ELSE research_checkpoints.retry_count
                END
            """, (
                ticker,
                stage,
                json.dumps(partial_results) if partial_results else None,
                error
            ))
            conn.commit()

    def generate_search_prompts(self, company_name: str) -> List[Dict]:
        """Generate search prompts for different research categories"""
        prompt_configs = [
            {
                "type": "environmental_safety",
                "system": f"""Generate a search strategy for {company_name} focused on environmental and safety issues.
                Consider: environmental damage, toxic spills, worker safety violations, workplace accidents, public health hazards.
                Include keywords like: toxic, spill, contamination, "safety violation", accident, death, injury, "OSHA citation"."""
            },
            {
                "type": "financial_legal",
                "system": f"""Generate a search strategy for {company_name} focused on financial and legal issues.
                Consider: fraud, embezzlement, insider trading, bribery, corruption, regulatory violations, lawsuits.
                Include keywords like: fraud, "SEC investigation", lawsuit, settlement, fine, "criminal charges", "regulatory action"."""
            },
            {
                "type": "ethical_social",
                "system": f"""Generate a search strategy for {company_name} focused on ethical and social issues.
                Consider: discrimination, harassment, labor disputes, human rights violations, political activities, social impact.
                Include keywords like: discrimination, harassment, "labor violation", protest, boycott, controversy, scandal."""
            }
        ]

        prompts = []
        for config in prompt_configs:
            messages = [
                {"role": "system", "content": config["system"]},
                {"role": "user", "content": f"Generate a structured search strategy for {company_name}"}
            ]
            
            response = call_deepseek_api(messages)
            if response:
                prompts.append({
                    "type": config["type"],
                    "content": response["choices"][0]["message"]["content"]
                })
            else:
                logging.error(f"Error generating prompt for {config['type']}")
                
        return prompts

    def execute_search(self, query: str, category: str, max_results: int = 10) -> List[Dict]:
        """Execute a search query and return results with enhanced metadata"""
        try:
            results = []
            search_results = self.search_utils.search(
                keywords=query,
                region="wt-wt",
                safesearch="moderate",
                max_results=max_results
            )
            
            for r in search_results:
                source = Source(
                    url=r.get('link', ''),
                    title=r.get('title', 'No title'),
                    snippet=r.get('body', 'No snippet available'),
                    domain='',  # Will be set in post_init
                    source_type='web',
                    category=category,
                    query_context=query,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    published_date=None  # Web search doesn't provide dates
                )
                
                results.append(source.__dict__)
            return results
        except Exception as e:
            logging.error(f"Error in search execution: {str(e)}")
            return []

    def execute_news_search(self, query: str, category: str, max_results: int = 10) -> List[Dict]:
        """Execute a news search query and return results with enhanced metadata"""
        try:
            results = []
            news_results = self.search_utils.news_search(
                keywords=query,
                region="wt-wt",
                max_results=max_results
            )
            
            for r in news_results:
                source = Source(
                    url=r.get('link', ''),
                    title=r.get('title', 'No title'),
                    snippet=r.get('body', 'No snippet available'),
                    domain='',  # Will be set in post_init
                    source_type='news',
                    category=category,
                    query_context=query,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    published_date=r.get('date')
                )
                
                results.append(source.__dict__)
            return results
        except Exception as e:
            logging.error(f"Error in news search execution: {str(e)}")
            return []

    def research_company(self, company: Dict, max_retries: int = 3):
        """Execute full research workflow for a company with checkpointing"""
        company_name = company['name']
        ticker = company['ticker']
        token_usage = {
            'total_tokens': 0,
            'calls': 0,
            'stages': {}
        }
        logging.info(f"Starting research for {company_name}")
        
        # Check for existing checkpoint
        checkpoint = self._get_checkpoint(ticker)
        if checkpoint:
            if checkpoint['retry_count'] >= max_retries:
                logging.error(f"Max retries ({max_retries}) exceeded for {company_name}. Last stage: {checkpoint['stage']}, Retry count: {checkpoint['retry_count']}")
                return None
            
            logging.info(f"Resuming research for {company_name} from stage {checkpoint['stage']}")
            partial_results = checkpoint['partial_results']
            if 'token_usage' in partial_results:
                token_usage = partial_results['token_usage']
        else:
            partial_results = {}
            
        try:
            # Stage 1: Company Context
            if not checkpoint or checkpoint['stage'] < CHECKPOINT_STAGES['CONTEXT']:
                logging.info(f"Generating company context for {company_name}")
                response = get_company_context(company_name, ticker)
                if response and isinstance(response, dict):
                    company_context = response["choices"][0]["message"]["content"]
                    if "token_usage" in response:
                        token_usage['stages']['context'] = response["token_usage"]
                        token_usage['total_tokens'] += response["token_usage"]["total_tokens"]
                        token_usage['calls'] += 1
                else:
                    company_context = response
                
                if company_context == "Error generating company context":
                    logging.error(f"Failed to generate company context for {company_name}")
                    self._update_checkpoint(ticker, CHECKPOINT_STAGES['CONTEXT'], partial_results, "Failed to generate company context")
                    return None
                    
                logging.info(f"Generated initial context for {company_name}")
                partial_results['company_context'] = company_context
                partial_results['token_usage'] = token_usage
                self._update_checkpoint(ticker, CHECKPOINT_STAGES['CONTEXT'], partial_results)
            else:
                company_context = partial_results['company_context']
            
            # Stage 2: Search Queries
            if not checkpoint or checkpoint['stage'] < CHECKPOINT_STAGES['QUERIES']:
                logging.info(f"Generating search queries for {company_name}")
                response = generate_search_queries(company_name, company_context)
                if isinstance(response, dict) and "choices" in response:
                    search_queries = json.loads(response["choices"][0]["message"]["content"])
                    if "token_usage" in response:
                        token_usage['stages']['queries'] = response["token_usage"]
                        token_usage['total_tokens'] += response["token_usage"]["total_tokens"]
                        token_usage['calls'] += 1
                else:
                    search_queries = response
                
                if not search_queries:
                    logging.error(f"Failed to generate search queries for {company_name}")
                    self._update_checkpoint(ticker, CHECKPOINT_STAGES['QUERIES'], partial_results, "Failed to generate search queries")
                    return None
                    
                logging.info(f"Generated {len(search_queries)} search queries for {company_name}")
                partial_results['search_queries'] = search_queries
                partial_results['token_usage'] = token_usage
                self._update_checkpoint(ticker, CHECKPOINT_STAGES['QUERIES'], partial_results)
            else:
                search_queries = partial_results['search_queries']
            
            # Stage 3: Execute Searches
            if not checkpoint or checkpoint['stage'] < CHECKPOINT_STAGES['SEARCH']:
                logging.info(f"Executing searches for {company_name}")
                all_results = []
                all_sources = []
                
                for query in search_queries:
                    logging.info(f"Executing search for {company_name}: {query['query']} ({query['category']})")
                    web_results = self.execute_search(
                        f"{company_name} {query['query']}",
                        category=query['category'],
                        max_results=10
                    )
                    news_results = self.execute_news_search(
                        f"{company_name} {query['query']}",
                        category=query['category'],
                        max_results=5
                    )
                    
                    if not web_results and not news_results:
                        logging.warning(f"No results found for query: {query['query']}")
                    
                    all_sources.extend(web_results)
                    all_sources.extend(news_results)
                    
                    all_results.append({
                        'category': query['category'],
                        'query': query['query'],
                        'rationale': query['rationale'],
                        'priority': query['priority'],
                        'web_results': web_results,
                        'news_results': news_results
                    })
                
                if not all_sources:
                    logging.error(f"No search results found for {company_name}")
                    self._update_checkpoint(ticker, CHECKPOINT_STAGES['SEARCH'], partial_results, "No search results found")
                    return None
                
                unique_sources = {
                    source['source_hash']: source 
                    for source in all_sources
                }.values()
                
                logging.info(f"Found {len(unique_sources)} unique sources for {company_name}")
                partial_results['research_results'] = all_results
                partial_results['sources'] = list(unique_sources)
                self._update_checkpoint(ticker, CHECKPOINT_STAGES['SEARCH'], partial_results)
            else:
                all_results = partial_results['research_results']
                unique_sources = partial_results['sources']
            
            # Stage 4: Generate Summary
            if not checkpoint or checkpoint['stage'] < CHECKPOINT_STAGES['SUMMARY']:
                logging.info(f"Generating summary for {company_name}")
                summary = generate_summary(all_results, company_name, company_context)
                if summary.startswith("Error generating summary"):
                    logging.error(f"Failed to generate summary for {company_name}")
                    self._update_checkpoint(ticker, CHECKPOINT_STAGES['SUMMARY'], partial_results, "Failed to generate summary")
                    return None
                partial_results['summary'] = summary
                self._update_checkpoint(ticker, CHECKPOINT_STAGES['SUMMARY'], partial_results)
            else:
                summary = partial_results['summary']
            
            # Stage 5: Extract Structured Data
            if not checkpoint or checkpoint['stage'] < CHECKPOINT_STAGES['STRUCTURED']:
                logging.info(f"Extracting structured data for {company_name}")
                structured_data = extract_structured_data(all_results, summary, company_name)
                if not structured_data:
                    logging.error(f"Failed to extract structured data for {company_name}")
                    self._update_checkpoint(ticker, CHECKPOINT_STAGES['STRUCTURED'], partial_results, "Failed to extract structured data")
                    return None
                partial_results['structured_data'] = structured_data
                
                # Add positive trends analysis
                logging.info(f"Analyzing positive trends for {company_name}")
                positive_trends = analyze_positive_trends({
                    'summary': summary,
                    'company_context': company_context,
                    'research_results': all_results
                }, company_name)
                partial_results['positive_trends'] = positive_trends
                
                self._update_checkpoint(ticker, CHECKPOINT_STAGES['STRUCTURED'], partial_results)
            else:
                structured_data = partial_results['structured_data']
                positive_trends = partial_results.get('positive_trends', {})
            
            # Combine final results
            final_results = {
                'company': company,
                'company_context': company_context,
                'search_queries': search_queries,
                'research_results': all_results,
                'summary': summary,
                'structured_data': structured_data,
                'positive_trends': positive_trends,  # Add positive trends to final results
                'sources': list(unique_sources),
                'metadata': {
                    'total_sources': len(unique_sources),
                    'sources_by_type': {
                        'web': len([s for s in unique_sources if s['source_type'] == 'web']),
                        'news': len([s for s in unique_sources if s['source_type'] == 'news'])
                    },
                    'sources_by_category': {
                        'environmental_safety': len([s for s in unique_sources if s['category'] == 'environmental_safety']),
                        'financial_legal': len([s for s in unique_sources if s['category'] == 'financial_legal']),
                        'ethical_social': len([s for s in unique_sources if s['category'] == 'ethical_social'])
                    },
                    'queries_by_priority': {
                        '1': len([q for q in search_queries if q['priority'] == 1]),
                        '2': len([q for q in search_queries if q['priority'] == 2]),
                        '3': len([q for q in search_queries if q['priority'] == 3])
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Update database schema to include positive trends
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    ALTER TABLE research_results 
                    ADD COLUMN IF NOT EXISTS positive_trends JSON
                """)
                conn.commit()
            
            # Store final results
            self.store_results_in_db(company, final_results)
            
            # Save to file
            output_dir = Path("research_results")
            output_dir.mkdir(exist_ok=True)
            
            # Save to combined results file
            timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
            combined_results = {
                "meta": {
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0",
                    "type": "search_analysis"
                },
                "companies": [
                    {
                        "company_name": company_name,
                        "symbol": ticker,
                        "analysis": {
                            "historical": structured_data,
                            "opportunities": positive_trends,  # Add positive trends
                            "evidence": {
                                "sources": list(unique_sources),
                                "queries": search_queries
                            },
                            "categorization": {
                                "product_issues": structured_data.get('product_issues', []),
                                "conduct_issues": structured_data.get('conduct_issues', []),
                                "tags": structured_data.get('tags', []),
                                "patterns": structured_data.get('patterns', {})
                            }
                        },
                        "metadata": {
                            "analysis_timestamp": datetime.now().isoformat(),
                            "data_confidence": structured_data.get('confidence_score'),
                            "opportunities_confidence": positive_trends.get('confidence_score')
                        }
                    }
                ]
            }
            
            json_path = output_dir / f"search_analysis_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(combined_results, f, indent=2)
            logging.info(f"Saved combined analysis results to {json_path}")
            
            # Mark as complete
            self._update_checkpoint(ticker, CHECKPOINT_STAGES['COMPLETE'], final_results)
            logging.info(f"Completed research for {company_name}")
            
            logging.info(f"Total API calls: {token_usage['calls']}, Total tokens used: {token_usage['total_tokens']}")
            return final_results
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error researching {company_name}: {error_msg}")
            self._update_checkpoint(ticker, checkpoint['stage'] if checkpoint else 0, partial_results, error_msg)
            return None

    def store_results_in_db(self, company: Dict, results: Dict):
        """Store research results and sources in database"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Update research_results table schema to include company context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_ticker TEXT NOT NULL UNIQUE,
                    company_context TEXT,
                    summary TEXT,
                    risk_score INTEGER,
                    recommendation TEXT,
                    confidence_score INTEGER,
                    structured_data JSON,
                    raw_results JSON,
                    search_queries JSON,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_ticker) REFERENCES companies (ticker)
                )
            """)
            
            # Insert sources
            for source in results['sources']:
                cursor.execute("""
                    INSERT OR REPLACE INTO research_sources 
                    (company_ticker, source_hash, url, title, snippet, domain, 
                     source_type, category, query_context, retrieved_at, published_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company['ticker'],
                    source['source_hash'],
                    source['url'],
                    source['title'],
                    source['snippet'],
                    source['domain'],
                    source['source_type'],
                    source['category'],
                    source['query_context'],
                    source['retrieved_at'],
                    source['published_date']
                ))
            
            # Insert or update results
            cursor.execute("""
                INSERT INTO research_results 
                (company_ticker, company_context, summary, risk_score, recommendation, confidence_score, 
                 structured_data, raw_results, search_queries, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (company_ticker) DO UPDATE SET
                company_context=excluded.company_context,
                summary=excluded.summary,
                risk_score=excluded.risk_score,
                recommendation=excluded.recommendation,
                confidence_score=excluded.confidence_score,
                structured_data=excluded.structured_data,
                raw_results=excluded.raw_results,
                search_queries=excluded.search_queries,
                metadata=excluded.metadata,
                created_at=CURRENT_TIMESTAMP
            """, (
                company['ticker'],
                results['company_context'],
                results['summary'],
                results['structured_data'].get('risk_score'),
                results['structured_data'].get('recommendation'),
                results['structured_data'].get('confidence_score'),
                json.dumps(results['structured_data']),
                json.dumps(results['research_results']),
                json.dumps(results['search_queries']),
                json.dumps(results['metadata'])
            ))
            
            conn.commit()

def run_batch_research(max_workers: int = 3):  # Reduced max_workers for rate limiting
    """Run research for top companies in parallel"""
    logging.info("Starting batch research workflow")
    
    companies = get_top_companies()
    workflow = ResearchWorkflow(timeout=30)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(workflow.research_company, company): company 
                  for company in companies}
        
        for future in tqdm(as_completed(futures), total=len(companies)):
            company = futures[future]
            try:
                result = future.result()
                if result:
                    logging.info(f"Successfully processed {company['name']}")
                else:
                    logging.error(f"Failed to process {company['name']}")
            except Exception as e:
                logging.error(f"Error processing {company['name']}: {str(e)}")

def get_incomplete_research() -> List[Dict]:
    """Get list of companies with incomplete research"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.name, c.ticker, c.tick, c.description,
                   rc.stage, rc.retry_count, rc.error_message, rc.last_updated
            FROM companies c
            LEFT JOIN research_checkpoints rc ON c.ticker = rc.company_ticker
            WHERE rc.stage IS NULL OR rc.stage < ?
            ORDER BY c.tick DESC
        """, (CHECKPOINT_STAGES['COMPLETE'],))
        
        return [
            {
                'name': row[0],
                'ticker': row[1],
                'tick': row[2],
                'description': row[3],
                'stage': row[4],
                'retry_count': row[5],
                'error': row[6],
                'last_updated': row[7]
            }
            for row in cursor.fetchall()
        ]

def get_research_status() -> Dict:
    """Get overall research workflow status"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN rc.stage = ? THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN rc.stage IS NULL THEN 1 ELSE 0 END) as not_started,
                SUM(CASE WHEN rc.stage > 0 AND rc.stage < ? THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN rc.retry_count >= 3 THEN 1 ELSE 0 END) as failed
            FROM companies c
            LEFT JOIN research_checkpoints rc ON c.ticker = rc.company_ticker
        """, (CHECKPOINT_STAGES['COMPLETE'], CHECKPOINT_STAGES['COMPLETE']))
        
        row = cursor.fetchone()
        return {
            'total': row[0],
            'completed': row[1],
            'not_started': row[2],
            'in_progress': row[3],
            'failed': row[4],
            'completion_percentage': (row[1] / row[0] * 100) if row[0] > 0 else 0
        }

def resume_research(max_workers: int = 3, max_retries: int = 3):
    """Resume research for incomplete companies, skipping investment products"""
    logging.info("Resuming research workflow")
    
    incomplete = get_incomplete_research()
    if not incomplete:
        logging.info("No incomplete research found")
        return
    
    # Filter out investment products
    operating_companies = []
    investment_products = []
    
    for company in incomplete:
        classification = is_investment_product(
            company['name'],
            company['ticker'],
            company['description']
        )
        if classification['is_investment_product']:
            investment_products.append({
                **company,
                **classification
            })
        else:
            operating_companies.append(company)
    
    logging.info(f"Filtered out {len(investment_products)} investment products")
    logging.info(f"Processing {len(operating_companies)} operating companies")
    
    # Log investment products for review
    for product in investment_products:
        logging.info(f"Skipping investment product: {product['name']} ({product['ticker']}) - "
                    f"Confidence: {product['confidence']}% - "
                    f"Matches: {', '.join(product['matches'])}")
    
    if not operating_companies:
        logging.info("No operating companies to process")
        return
    
    workflow = ResearchWorkflow(timeout=30)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(workflow.research_company, company, max_retries): company 
            for company in operating_companies
        }
        
        for future in tqdm(as_completed(futures), total=len(operating_companies)):
            company = futures[future]
            try:
                result = future.result()
                if result:
                    logging.info(f"Successfully processed {company['name']}")
                else:
                    logging.error(f"Failed to process {company['name']}")
            except Exception as e:
                logging.error(f"Error processing {company['name']}: {str(e)}")
    
    status = get_research_status()
    logging.info(f"Research status: {json.dumps(status, indent=2)}")

def analyze_positive_trends(company_results: Dict, company_name: str) -> Dict:
    """Analyze positive trends and opportunities from research results"""
    try:
        context = f"""Company: {company_name}

Summary of findings:
{company_results.get('summary', '')}

Company Context:
{company_results.get('company_context', '')}

Analyze the above information and identify positive trends and opportunities. Respond with ONLY a JSON object in this exact format:
{{
    "growth_opportunities": [
        {{
            "opportunity": "Description of opportunity",
            "strength": "high|medium|low",
            "timeframe": "near-term|medium-term|long-term"
        }}
    ],
    "competitive_advantages": [
        "List of key competitive advantages"
    ],
    "innovation_leadership": {{
        "areas": ["List of innovation areas"],
        "initiatives": ["Key innovation initiatives"]
    }},
    "esg_strengths": {{
        "environmental": ["Environmental strengths"],
        "social": ["Social impact strengths"],
        "governance": ["Governance strengths"]
    }},
    "market_position": {{
        "current_strengths": ["Current market strengths"],
        "future_potential": ["Future opportunities"]
    }},
    "confidence_score": 75
}}"""

        messages = [
            {"role": "system", "content": """You are a business analyst focused on identifying growth opportunities 
            and positive trends. Respond ONLY with a properly formatted JSON object - no additional text or explanation."""},
            {"role": "user", "content": context}
        ]
        
        logging.info(f"Analyzing positive trends for {company_name}")
        response = call_deepseek_api(messages, temperature=0.2)
        
        if not response or "choices" not in response:
            logging.error("No valid response from API for positive trends analysis")
            return {}
            
        try:
            content = response["choices"][0]["message"]["content"].strip()
            
            # Try to find JSON object in the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                logging.error(f"No JSON object found in response: {content}")
                return {}
                
            json_str = json_match.group()
            # Remove any comments or trailing commas
            json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            data = json.loads(json_str)
            
            # Validate the structure
            required_fields = [
                'growth_opportunities', 'competitive_advantages', 'innovation_leadership',
                'esg_strengths', 'market_position', 'confidence_score'
            ]
            
            if not all(field in data for field in required_fields):
                logging.error(f"Missing required fields in positive trends data: {data}")
                return {}
                
            # Ensure confidence score is in valid range
            if not isinstance(data['confidence_score'], (int, float)):
                data['confidence_score'] = 50
            data['confidence_score'] = max(0, min(100, data['confidence_score']))
            
            logging.info(f"Successfully analyzed positive trends for {company_name}")
            return data
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse positive trends response: {str(e)}\nContent: {content}")
            return {}
        except Exception as e:
            logging.error(f"Error processing positive trends response: {str(e)}")
            return {}
            
    except Exception as e:
        logging.error(f"Error in positive trends analysis: {str(e)}")
        return {}

def retroactive_positive_analysis():
    """Run positive trends analysis on all previously completed companies"""
    logging.info("Starting retroactive positive trends analysis")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # First ensure the positive_trends column exists
        try:
            cursor.execute("ALTER TABLE research_results ADD COLUMN positive_trends JSON")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise e
        
        # Now get all completed companies that don't have positive trends analysis
        cursor.execute("""
            SELECT r.company_ticker, r.company_context, r.summary, r.raw_results,
                   c.name, c.description
            FROM research_results r
            JOIN companies c ON r.company_ticker = c.ticker
            WHERE r.positive_trends IS NULL
            AND r.structured_data IS NOT NULL
        """)
        
        companies = cursor.fetchall()
        logging.info(f"Found {len(companies)} companies needing positive trends analysis")
        
        for company in tqdm(companies, desc="Analyzing positive trends"):
            try:
                ticker, context, summary, raw_results, name, description = company
                
                positive_trends = analyze_positive_trends({
                    'summary': summary,
                    'company_context': context,
                    'research_results': json.loads(raw_results) if raw_results else {}
                }, name)
                
                if positive_trends:
                    cursor.execute("""
                        UPDATE research_results 
                        SET positive_trends = ?
                        WHERE company_ticker = ?
                    """, (json.dumps(positive_trends), ticker))
                    conn.commit()
                    logging.info(f"Added positive trends analysis for {name}")
                else:
                    logging.error(f"Failed to generate positive trends for {name}")
                    
            except Exception as e:
                logging.error(f"Error analyzing positive trends for {name}: {str(e)}")
                continue
        
        logging.info("Completed retroactive positive trends analysis")

def main():
    """Main entry point for the research workflow"""
    logging.info("Starting research workflow")
    run_batch_research()
    logging.info("Completed research workflow")

if __name__ == "__main__":
    # Add command line argument parsing
    import argparse
    parser = argparse.ArgumentParser(description='Research workflow management')
    parser.add_argument('--retroactive', action='store_true', help='Run retroactive positive trends analysis')
    args = parser.parse_args()
    
    if args.retroactive:
        retroactive_positive_analysis()
    else:
        main() 