import json
from typing import List, Optional

from app.services.prompt.prompt_loader import PromptLoader
from app.models.domain.fsm.interrogation import InterrogationState, AllowedMoves

class SuspectAgent:
    '''
    --- deprecated
    '''
    def __init__(self, llm_client):
        self.llm = llm_client
        self.system_prompt_template = PromptLoader.load("app/prompts/chat/system.txt")

    async def chat_generate(self,
                            suspect_personality: dict,
                            user_message: str,
                            history: dict,
                            clues: Optional[List[dict]] = None) -> str:
        # 1. Update Interrogation State (FSM)
        self._update_interrogation_state(suspect_personality, user_message, clues or [])

        # 2. Extract & Format Data for Prompt
        state_data = suspect_personality.get("interrogation_state", {})
        metrics = state_data.get("metrics", {})

        # Helper to format complex fields as JSON strings
        def format_field(key):
            data = suspect_personality.get(key)
            if not data:
                return "No information."
            return json.dumps(data, ensure_ascii=False, indent=2)

        # Determine current secrets based on state
        # Handle both string and Enum for safety
        raw_state = state_data.get("state", InterrogationState.DEFENSIVE)
        if isinstance(raw_state, InterrogationState):
            current_state_key = raw_state.value.lower()
        else:
            current_state_key = str(raw_state).lower()

        secrets_map = suspect_personality.get("secrets_by_stage", {})
        current_secrets = secrets_map.get(current_state_key, [])

        # Format clue list
        clue_seen = suspect_personality.get("clue_seen", [])
        clue_str = "\n".join([f"- {e['id']} (Weight: {e.get('weight', 0)})" for e in clue_seen]) or "No clue presented yet."

        # Construct prompt data
        prompt_data = {
            "name": suspect_personality.get("name", "Unknown"),
            "role": suspect_personality.get("role", "Unknown"),
            "age": suspect_personality.get("age", "Unknown"),
            "gender": suspect_personality.get("gender", "Unknown"),
            "description": suspect_personality.get("description", "Unknown"),
            "incident_summary": suspect_personality.get("incident_summary", "Unknown incident."),
            "primary_location": suspect_personality.get("primary_location", "Unknown location."),
            "time_memory": format_field("time_memory"),
            "observation": format_field("observation"),
            "answering_rule": format_field("answering_rule"),
            "truth_model": format_field("truth_model"),
            # FSM Fields
            "current_state": state_data.get("state", InterrogationState.DEFENSIVE),
            "pressure_level": metrics.get("pressure", 0),
            "allowed_moves": ", ".join(state_data.get("allowed_moves", AllowedMoves.DEFENSIVE)),
            "clue_list": clue_str,
            "current_secrets": json.dumps(current_secrets, ensure_ascii=False, indent=2),
            "chat_history": "\n".join(
                f"{entry['role']}: {entry['content']}"
                for entry in history.get("chat_history", [])
            )
        }

        formatted_system_prompt = self.system_prompt_template.format(**prompt_data)
        response = self.llm.complete(system=formatted_system_prompt, user=user_message)
        return response

    def _update_interrogation_state(self,
                                    suspect: dict,
                                    user_msg: str,
                                    new_clues: List[dict]):
        """
        Deterministically updates the interrogation state based on inputs.
        Modifies suspect dict in-place.
        """
        # Ensure structure exists
        if "interrogation_state" not in suspect:
            suspect["interrogation_state"] = {
                "state": InterrogationState.DEFENSIVE,
                "metrics": {"pressure": 0, "contradictions": 0, "clue_weight_seen": 0, "trust_in_interrogator": 0},
                "allowed_moves": AllowedMoves.DEFENSIVE
            }
        if "clue_seen" not in suspect:
            suspect["clue_seen"] = []

        state_data = suspect["interrogation_state"]
        metrics = state_data["metrics"]

        # Normalize current state to Enum
        raw_current = state_data.get("state", InterrogationState.DEFENSIVE)
        if isinstance(raw_current, str):
            try:
                current_state = InterrogationState(raw_current)
            except ValueError:
                current_state = InterrogationState.DEFENSIVE
        else:
            current_state = raw_current

        # --- 1. Update Metrics ---
        # Clue Processing
        for ev in new_clues:
            # Check if already seen to avoid duplicate pressure
            existing_ids = {e["id"] for e in suspect["clue_seen"]}
            if ev["id"] not in existing_ids:
                suspect["clue_seen"].append(ev)
                weight = ev.get("weight", 0)
                metrics["clue_weight_seen"] += weight
                metrics["pressure"] += weight

        # Contradiction Detection (Dynamic Keyword Rule)
        truth_model = suspect.get("truth_model", {})
        hidden_topics = truth_model.get("hide_topics", [])

        time_keywords = ["시간", "언제", "시", "분", "time", "when"]
        if any(topic in user_msg for topic in hidden_topics) and any(tk in user_msg for tk in time_keywords):
            metrics["pressure"] += 15

        # --- 2. Check Transitions ---
        seen_ids = {e["id"] for e in suspect["clue_seen"]}
        next_state = current_state
        
        # Get dynamic critical clue IDs
        critical_ids = suspect.get("critical_clue_ids", [])

        if current_state == InterrogationState.DEFENSIVE:
            if (metrics["pressure"] >= 65 or
                metrics["contradictions"] >= 2 or
                metrics["clue_weight_seen"] >= 60):
                next_state = InterrogationState.CORNERED

        elif current_state == InterrogationState.CORNERED:
            # Trigger breakdown if pressure is high, contradictions are frequent,
            # or if ANY critical clue has been revealed (shaking their confidence).
            has_seen_any_critical = any(cid in seen_ids for cid in critical_ids)
            
            if (metrics["pressure"] >= 85 or
                metrics["contradictions"] >= 3 or
                has_seen_any_critical):
                next_state = InterrogationState.BREAKDOWN

        elif current_state == InterrogationState.BREAKDOWN:
            # Trigger confession only if ALL critical clue has been presented.
            has_seen_all_critical = all(cid in seen_ids for cid in critical_ids)
            
            # If critical_ids list is empty, we avoid auto-confession to prevent bugs.
            if critical_ids and has_seen_all_critical:
                next_state = InterrogationState.CONFESSION

        # --- 3. Apply Transition ---
        if next_state != current_state:
            state_data["state"] = next_state
            state_data["last_transition_reason"] = f"Pressure: {metrics['pressure']}, Clue: {len(seen_ids)}"
            # Update Allowed Moves using Enum logic
            state_data["allowed_moves"] = AllowedMoves.get_moves(next_state)