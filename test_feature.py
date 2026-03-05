# Test feature - intentionally has some issues for DevPilot to review
def calculate_discount(price, discount_pct):
    # BUG: no validation on inputs
    return price * (1 - discount_pct / 100)

def get_user(user_id):
    # SECURITY: SQL injection vulnerability (for demo purposes)
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

class DataProcessor:
    def process(self, data):
        result = []
        for i in range(len(data)):  # STYLE: should use enumerate
            result.append(data[i] * 2)
        return result
