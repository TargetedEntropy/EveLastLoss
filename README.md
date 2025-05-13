### Get Last Loss

Run it from the command line with your access token and character ID:

python eve_last_loss.py YOUR_ACCESS_TOKEN YOUR_CHARACTER_ID

--

### Get Token

Before using this script:

* Register an application at https://developers.eveonline.com/
* Set the callback URL to http://localhost:8080/callback
* Replace YOUR_CLIENT_ID and YOUR_CLIENT_SECRET in the script, `get_token.py` with your actual values

The script will:

* Open your browser to the EVE Online login page
* Have you log in and authorize the application
* Automatically capture the authorization code via the redirect
* Exchange the code for an access token
* Extract and display your character ID
* Save the token and character info to a file for later use
* Show you how to use this token with the ship loss tracker script

