from flask import Blueprint, jsonify
from services.data_agent import DataIntelligenceAgent

intelligence_bp = Blueprint('intelligence', __name__)

@intelligence_bp.route('/api/intelligence/<entity_name>', methods=['GET'])
def get_entity_intelligence(entity_name):
    """
    Triggers the resilient Data Intelligence Agent.
    Guaranteed to return structured JSON.
    """
    agent = DataIntelligenceAgent(entity_name)
    result = agent.execute()
    
    return jsonify(result), 200
