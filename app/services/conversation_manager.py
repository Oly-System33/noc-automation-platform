class ConversationManager:

    def __init__(self):
        self.conversations = {}

    def start(self, user_id):
        self.conversations[user_id] = {
            "state": "SELECT_PROJECT",
            "data": {}
        }

    def get(self, user_id):
        return self.conversations.get(user_id)

    def update_state(self, user_id, state):
        if user_id in self.conversations:
            self.conversations[user_id]["state"] = state

    def update_data(self, user_id, key, value):
        if user_id in self.conversations:
            self.conversations[user_id]["data"][key] = value

    def end(self, user_id):
        if user_id in self.conversations:
            del self.conversations[user_id]


conversation_manager = ConversationManager()
