import requests
import datetime
import sys
from dateutil import parser

def get_time_since_last_ship_loss(access_token, character_id):
    # EVE ESI API endpoint for killmails
    url = f"https://esi.evetech.net/latest/characters/{character_id}/killmails/recent/"
    
    # Set up headers with authorization
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get killmail history
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        killmails = response.json()
        
        # Filter for losses (where character_id is the victim)
        losses = []
        for kill in killmails:
            # Get detailed killmail info
            kill_id = kill['killmail_id']
            kill_hash = kill['killmail_hash']
            kill_url = f"https://esi.evetech.net/latest/killmails/{kill_id}/{kill_hash}/"
            
            kill_response = requests.get(kill_url)
            kill_response.raise_for_status()
            kill_detail = kill_response.json()
            
            # Check if our character was the victim
            if kill_detail['victim']['character_id'] == int(character_id):
                losses.append(kill_detail)
        
        if not losses:
            return "No ship losses found for this character."
        
        # Get the most recent loss
        most_recent_loss = max(losses, key=lambda x: parser.parse(x['killmail_time']))
        loss_time = parser.parse(most_recent_loss['killmail_time'])
        
        # Calculate time difference
        now = datetime.datetime.now(datetime.timezone.utc)
        time_diff = now - loss_time
        
        # Format the time difference
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Create human-readable output
        result = "Time since last ship loss: "
        if days > 0:
            result += f"{days} day{'s' if days != 1 else ''}, "
        if hours > 0:
            result += f"{hours} hour{'s' if hours != 1 else ''}, "
        if minutes > 0:
            result += f"{minutes} minute{'s' if minutes != 1 else ''}, "
        result += f"{seconds} second{'s' if seconds != 1 else ''}"
        
        # Add ship info if available
        if 'ship_type_id' in most_recent_loss['victim']:
            ship_type_id = most_recent_loss['victim']['ship_type_id']
            ship_response = requests.get(f"https://esi.evetech.net/latest/universe/types/{ship_type_id}/")
            if ship_response.status_code == 200:
                ship_info = ship_response.json()
                result += f"\nLost ship: {ship_info['name']}"
        
        return result
        
    except requests.exceptions.RequestException as e:
        return f"Error accessing EVE Online API: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python eve_last_loss.py <access_token> <character_id>")
        sys.exit(1)
    
    access_token = sys.argv[1]
    character_id = sys.argv[2]
    
    result = get_time_since_last_ship_loss(access_token, character_id)
    print(result)