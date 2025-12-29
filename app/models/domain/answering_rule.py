class AnsweringRule:
    # NPC의 이상한 부분을 바로 잡기 위하여
    def __init__(self,
                 minute_precision_allowed: bool,
                 unknown_reply_policy: str,
                 out_of_incident_time_policy: str,
    ):
        self.minute_precision_allowed = minute_precision_allowed
        self.unknown_reply_policy = unknown_reply_policy
        self.out_of_incident_time_policy = out_of_incident_time_policy