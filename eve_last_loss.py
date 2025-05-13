import requests
import datetime
import sys
from dateutil import parser


class EveOnlineAPI:
    """Class to handle EVE Online API interactions and ship loss tracking."""

    BASE_URL = "https://esi.evetech.net/latest"

    def __init__(self, access_token, character_id):
        """Initialize with authentication and character information."""
        self.access_token = access_token
        self.character_id = int(character_id)
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint, params=None):
        """Make a request to the EVE ESI API and handle errors."""
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error accessing EVE Online API: {str(e)}")

    def get_recent_killmails(self):
        """Retrieve recent killmails for the character."""
        endpoint = f"/characters/{self.character_id}/killmails/recent/"
        return self._make_request(endpoint)

    def get_killmail_details(self, kill_id, kill_hash):
        """Get detailed information about a specific killmail."""
        endpoint = f"/killmails/{kill_id}/{kill_hash}/"
        return self._make_request(endpoint)

    def get_ship_info(self, ship_type_id):
        """Get information about a ship type."""
        endpoint = f"/universe/types/{ship_type_id}/"
        return self._make_request(endpoint)

    def filter_character_losses(self, killmails):
        """Filter killmails to only include those where the character was the victim."""
        losses = []
        for kill in killmails:
            kill_detail = self.get_killmail_details(
                kill['killmail_id'],
                kill['killmail_hash']
            )
            if kill_detail['victim']['character_id'] == self.character_id:
                losses.append(kill_detail)
        return losses

    def find_most_recent_loss(self, losses):
        """Find the most recent ship loss from a list of losses."""
        if not losses:
            return None
        return max(losses, key=lambda x: parser.parse(x['killmail_time']))

    def format_time_difference(self, time_diff):
        """Format a time difference into a human-readable string."""
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        result = "Time since last ship loss: "
        if days > 0:
            result += f"{days} day{'s' if days != 1 else ''}, "
        if hours > 0:
            result += f"{hours} hour{'s' if hours != 1 else ''}, "
        if minutes > 0:
            result += f"{minutes} minute{'s' if minutes != 1 else ''}, "
        result += f"{seconds} second{'s' if seconds != 1 else ''}"

        return result

    def get_time_since_last_ship_loss(self):
        """Calculate and format the time since the character's last ship loss."""
        try:
            # Get killmail history and filter for losses
            killmails = self.get_recent_killmails()
            losses = self.filter_character_losses(killmails)

            if not losses:
                return "No ship losses found for this character."

            # Get the most recent loss and its details
            most_recent_loss = self.find_most_recent_loss(losses)
            loss_time = parser.parse(most_recent_loss['killmail_time'])

            # Calculate time difference
            now = datetime.datetime.now(datetime.timezone.utc)
            time_diff = now - loss_time

            # Format the result
            result = self.format_time_difference(time_diff)

            # Add ship info if available
            if 'ship_type_id' in most_recent_loss['victim']:
                ship_type_id = most_recent_loss['victim']['ship_type_id']
                try:
                    ship_info = self.get_ship_info(ship_type_id)
                    result += f"\nLost ship: {ship_info['name']}"
                except Exception:
                    # If we can't get the ship info, just continue without it
                    pass

            return result

        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"


def main():
    """Main function to run the script from command line."""
    if len(sys.argv) != 3:
        print("Usage: python eve_last_loss.py <access_token> <character_id>")
        sys.exit(1)

    access_token = sys.argv[1]
    character_id = sys.argv[2]

    eve_api = EveOnlineAPI(access_token, character_id)
    result = eve_api.get_time_since_last_ship_loss()
    print(result)


if __name__ == "__main__":
    main()
