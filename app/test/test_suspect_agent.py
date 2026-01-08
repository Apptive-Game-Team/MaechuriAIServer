from app.services.npc.suspect_service import SuspectService
import json

service = SuspectService()

pre_json = {
    "case_context": {
        "incident_time": {"start": "10:00", "end": "14:00"},
        "primary_location": "창고",
        "incident_type": "theft",
        "summary": "카페 창고에서 영수증이 사라졌다."
    },
    "world_context": {
        "locations": ["카운터", "창고"],
        "evidence_types": ["receipt"],
        "visibility_rules": [
            {
                "evidence_type": "receipt",
                "from": "창고",
                "can_see": ["suspects", "player"],
                "cannot_see": []
            }
        ]
    },
    "ground_truth": {
        "crime_time_range": {"start": "10:30", "end": "11:00"},
        "crime_location": "창고",
        "culprit_count": 1,
        "method": "훔쳐감",
        "required_evidence": [
            {
                "type": "receipt",
                "min_count": 1
            }
        ]
    },
    "generation_config": {
        "suspect_count": 1,
        "difficulty": "easy",
        "anchor_events_range": [1, 2],
        "routines_range": [1, 2],
        "allow_lying": False,
        "liar_ratio": 0.0,
        "ambiguity_level": "low"
    },
    "constraints": None
}
post_json = service.generate(pre_json)

print(json.dumps(post_json, indent=2, ensure_ascii=False))
