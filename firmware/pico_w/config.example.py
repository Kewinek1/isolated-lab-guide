# Copy into the PRIVATE working area as config.py; upload that copy to the Pico W.
# The shared tree must retain only this example.
ENABLE_NETWORK = False
WIFI_SSID = "REPLACE_WITH_ISOLATED_LAB_SSID"
WIFI_PASSWORD = "REPLACE_WITH_LAB_WIFI_PASSWORD"
COUNTRY = "XX"  # Replace with the installation country's two-letter code.
PORT = 8080

# "token" requires Authorization: Bearer <API_TOKEN> on every request.
# "lab" deliberately removes authentication; also requires the flag below.
MODE = "token"
ALLOW_UNAUTHENTICATED_LAB = False
API_TOKEN = "REPLACE_WITH_64_HEX_CHARACTERS"
