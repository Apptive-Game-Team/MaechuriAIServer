
import pytest
from app.services.agent.suspect_agent import SuspectAgent

class MockLLM:
    def complete(self, system, user):
        return "Mock response"

@pytest.fixture
def agent():
    return SuspectAgent(MockLLM())

@pytest.fixture
def base_suspect():
    return {
        "name": "Test Suspect",
        "truth_model": {
            "hide_topics": ["secret_location", "weapon"],
            "is_lying": True
        },
        "interrogation_state": {
            "state": "DEFENSIVE",
            "metrics": {"pressure": 0, "contradictions": 0, "evidence_weight_seen": 0, "trust_in_interrogator": 0},
            "allowed_moves": ["deny"]
        },
        "secrets_by_stage": {
            "cornered": ["I was near the location"],
            "confession": ["I did it"]
        },
        "evidence_seen": []
    }

def test_initial_state(agent, base_suspect):
    # Ensure defaults are respected
    assert base_suspect["interrogation_state"]["state"] == "DEFENSIVE"

def test_pressure_increase_with_evidence(agent, base_suspect):
    evidence = [{"id": "weak_evidence", "weight": 10}]
    agent._update_interrogation_state(base_suspect, "Hello", evidence)
    
    metrics = base_suspect["interrogation_state"]["metrics"]
    assert metrics["pressure"] == 10
    assert metrics["evidence_weight_seen"] == 10
    assert len(base_suspect["evidence_seen"]) == 1

def test_transition_to_cornered(agent, base_suspect):
    # Add enough pressure to trigger CORNERED (threshold 65)
    evidence = [{"id": "strong_evidence", "weight": 70}]
    agent._update_interrogation_state(base_suspect, "Explain this!", evidence)
    
    state_data = base_suspect["interrogation_state"]
    assert state_data["state"] == "CORNERED"
    assert "partial_admit" in state_data["allowed_moves"]

def test_dynamic_contradiction_detection(agent, base_suspect):
    # Topic "secret_location" is in hide_topics
    # User asks "When were you at secret_location?"
    user_msg = "언제 secret_location에 있었어?"
    
    agent._update_interrogation_state(base_suspect, user_msg, [])
    
    metrics = base_suspect["interrogation_state"]["metrics"]
    # Should increase pressure by 15
    assert metrics["pressure"] == 15

def test_transition_to_confession(agent, base_suspect):
    # Force state to BREAKDOWN first
    base_suspect["interrogation_state"]["state"] = "BREAKDOWN"
    
    # Present critical evidence
    evidence = [
        {"id": "LOCKED_ROOM_TOOL", "weight": 50},
        {"id": "POISON_INJECTION_TRACE", "weight": 50}
    ]
    agent._update_interrogation_state(base_suspect, "It's over.", evidence)
    
    state_data = base_suspect["interrogation_state"]
    assert state_data["state"] == "CONFESSION"
    assert "full_confession" in state_data["allowed_moves"]
