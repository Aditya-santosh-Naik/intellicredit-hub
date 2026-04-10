import logging
from services.data_sources import get_news_data, get_corporate_data, get_litigation_data

logger = logging.getLogger(__name__)

class DataIntelligenceAgent:
    """
    Orchestrates the data collection and enforces the structure.
    Always returns valid JSON regardless of failures.
    """
    
    def __init__(self, entity_name):
        self.entity_name = entity_name
        self.data_sources_used = []
        self.api_failures_logged = []
        
    def execute(self):
        """Builds the structured profile."""
        
        # 1. Fetch News
        news_result = get_news_data(self.entity_name)
        if news_result['source_used'] != "None":
            self.data_sources_used.append(news_result['source_used'])
        self.api_failures_logged.extend(news_result['failures'])
        
        # 2. Fetch Corporate Data
        corp_result = get_corporate_data(self.entity_name)
        if corp_result['source_used'] != "None":
            self.data_sources_used.append(corp_result['source_used'])
        self.api_failures_logged.extend(corp_result['failures'])
            
        # 3. Fetch Litigation Data
        litigation_result = get_litigation_data(self.entity_name)
        if litigation_result['source_used'] != "None":
            self.data_sources_used.append(litigation_result['source_used'])
        self.api_failures_logged.extend(litigation_result['failures'])
        
        
        # -- Structuring --
        # Extract individual chunks, defaulting to empty or safe types dynamically
        
        # News mapping
        news_sentiment = news_result.get('data', {}).get('sentiment', 'Not Available')
        if type(news_sentiment) is not str:
            news_sentiment = 'Not Available'
            
        sector_signals = news_result.get('data', {}).get('signals', {})
        if type(sector_signals) is not dict:
            sector_signals = {}
            
        # Corporate mapping
        promoter_intel = corp_result.get('data', {}).get('promoter_intel', {})
        if type(promoter_intel) is not dict:
            promoter_intel = {}
            
        # Litigation mapping
        cases = litigation_result.get('data', {}).get('cases', [])
        if type(cases) is not list:
             cases = []
             
        flags = litigation_result.get('data', {}).get('regulatory_flags', [])
        if type(flags) is not list:
            flags = []

        # Validate values (duplicate removal on lists)
        cases = self._remove_duplicates(cases)
        flags = self._remove_duplicates(flags)

        confidence_score = self._calculate_confidence()

        return {
            "entity_name": self.entity_name,
            "news_sentiment": news_sentiment,
            "litigation_cases": cases,
            "regulatory_flags": flags,
            "promoter_intelligence": promoter_intel,
            "sector_signals": sector_signals,
            "confidence_score": confidence_score,
            "data_sources_used": self.data_sources_used,
            "api_failures_logged": self.api_failures_logged
        }
        
    def _remove_duplicates(self, ds_list):
        if not ds_list: 
            return []
        try:
            return [dict(t) for t in {tuple(d.items()) for d in ds_list}]
        except Exception:
            # Fallback if unhashable dicts
            return ds_list

    def _calculate_confidence(self):
        """
        High -> verified across 2+ sources
        Medium -> verified from single credible source
        Low -> inferred from weak signals
        """
        valid_sources = len(self.data_sources_used)
        if valid_sources >= 2:
            return "High"
        elif valid_sources == 1:
            return "Medium"
        else:
            return "Low"
