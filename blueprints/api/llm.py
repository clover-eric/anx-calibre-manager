import requests
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _

llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

@llm_bp.route('/models', methods=['POST'])
def get_llm_models():
    """
    Fetches the list of available LLM models from an OpenAI-compatible API.
    """
    if not g.user or not g.user.id:
        return jsonify({'error': _('Authentication required.')}), 401

    data = request.get_json()
    base_url = data.get('base_url')
    api_key = data.get('api_key')

    if not base_url or not api_key:
        return jsonify({'error': _('Base URL and API Key are required.')}), 400

    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    # Ensure the URL is correctly formed
    if not base_url.endswith('/'):
        base_url += '/'
    
    models_url = f"{base_url}models"

    try:
        response = requests.get(models_url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        models_data = response.json()
        
        # Extract model IDs from the response data
        # OpenAI format is a dictionary with a 'data' key which is a list of objects
        if 'data' in models_data and isinstance(models_data['data'], list):
            model_ids = sorted([model['id'] for model in models_data['data'] if 'id' in model])
            return jsonify(model_ids)
        else:
            # Handle other possible (but less common) structures if necessary
            return jsonify({'error': _('Unexpected response format from model provider.')}), 500

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if '401' in error_message:
            return jsonify({'error': _('Authentication error. Please check your API Key.')}), 401
        elif '404' in error_message:
             return jsonify({'error': _('Invalid API endpoint. Please check your Base URL.')}), 404
        else:
            return jsonify({'error': _('Could not connect to the model provider: %(error)s', error=error_message)}), 500
    except Exception as e:
        return jsonify({'error': _('An unexpected error occurred: %(error)s', error=str(e))}), 500