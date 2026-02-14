# Sports Tracker

# This script is a simple sports tracker that allows users to log their sports activities.
class SportsTracker:
    def __init__(self):
        self.activities = []

    def log_activity(self, sport, duration):
        self.activities.append({'sport': sport, 'duration': duration})
        print(f"Logged {duration} minutes of {sport}.\n")

    def show_activities(self):
        if not self.activities:
            print("No activities logged yet.")
            return
        print("Activities logged:")
        for activity in self.activities:
            print(f"Sport: {activity['sport']}, Duration: {activity['duration']} minutes")

# Example Usage
tracker = SportsTracker()
tracker.log_activity('Basketball', 90)
tracker.log_activity('Running', 30)
tracker.show_activities()