from flask import Blueprint, jsonify
from app.models import Location, SetupType
from app.services.objective import DEFECT_TYPES, CRITICAL_DEFECT_TYPES

master_bp = Blueprint('master', __name__, url_prefix='/api/master')


@master_bp.route('', methods=['GET'])
def get_master_data():
    locations = Location.query.all()
    location_list = [
        {
            'location_id': loc.location_id,
            'location_name': loc.location_name
        }
        for loc in locations
    ]
    
    setup_types = SetupType.query.all()
    setup_type_list = [
        {
            'setup_type_id': st.setup_type_id,
            'setup_name': st.setup_name,
            'setup_cost_minutes': st.setup_cost_minutes
        }
        for st in setup_types
    ]
    
    defect_type_list = [
        {
            'id': dt_id,
            'name': dt_name,
            'is_critical': dt_id in CRITICAL_DEFECT_TYPES
        }
        for dt_id, dt_name in DEFECT_TYPES.items()
    ]
    
    return jsonify({
        'locations': location_list,
        'setup_types': setup_type_list,
        'defect_types': defect_type_list
    }), 200