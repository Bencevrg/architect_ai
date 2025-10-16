# Segédfüggvények pl. JSON validáció, logging

import json

def validate_json(data):
    try:
        json.dumps(data)
        return True
    except Exception as e:
        print("Invalid JSON:", e)
        return False
