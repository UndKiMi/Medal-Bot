import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVIS_DIR = os.path.join(BASE_DIR, "AVIS")
DATA_DIR = os.path.join(BASE_DIR, "data")

AVIS_FILE = os.path.join(AVIS_DIR, "avis_drive.txt")

CHROME_OPTIONS = {
    'languages': os.getenv('CHROME_LANGUAGES', 'fr-FR,fr').split(','),
    'user_agent': os.getenv('CHROME_USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
    'window_size': os.getenv('CHROME_WINDOW_SIZE', '1920,1080'),
    'vendor': os.getenv('CHROME_VENDOR', 'Google Inc.'),
    'platform': os.getenv('CHROME_PLATFORM', 'Win32'),
    'webgl_vendor': os.getenv('CHROME_WEBGL_VENDOR', 'Intel Inc.'),
    'renderer': os.getenv('CHROME_RENDERER', 'Intel Iris OpenGL Engine'),
}

TIMING = {
    'short_wait': (int(os.getenv('TIMING_SHORT_WAIT_MIN', '1')), int(os.getenv('TIMING_SHORT_WAIT_MAX', '3'))),
    'medium_wait': (int(os.getenv('TIMING_MEDIUM_WAIT_MIN', '3')), int(os.getenv('TIMING_MEDIUM_WAIT_MAX', '7'))),
    'long_wait': (int(os.getenv('TIMING_LONG_WAIT_MIN', '5')), int(os.getenv('TIMING_LONG_WAIT_MAX', '10'))),
    'min_total_duration': int(os.getenv('TIMING_MIN_TOTAL_DURATION', '60')),
}

# XPath des éléments importants
XPATHS = {
    'start_button': "//button[contains(., 'Commencer') or contains(., 'Start')]",
    'next_button': "//button[contains(., 'Suivant') or contains(., 'Next')]",
    'radio_input': "input[type='radio']",
    'textarea': "textarea",
    'date_input': "//input[@type='date' or @placeholder='JJ/MM/AAAA']",
    'time_inputs': "//input[contains(@placeholder, 'HH') or contains(@placeholder, 'MM')]",
    'restaurant_input': "//input[contains(@placeholder, 'restaurant') or contains(@placeholder, 'code')]"
}

# Mapping des fichiers d'avis
AVIS_MAPPING = {
    'borne_sur_place': os.path.join(AVIS_DIR, "avis_borne_sur_place.txt"),
    'borne_emporter': os.path.join(AVIS_DIR, "avis_borne_a_emporter.txt"),
    'comptoir_sur_place': os.path.join(AVIS_DIR, "avis_comptoir_sur_place.txt"),
    'comptoir_emporter': os.path.join(AVIS_DIR, "avis_comptoir_emporte.txt"),
    'drive': os.path.join(AVIS_DIR, "avis_drive.txt"),
    'cc_appli_comptoir': os.path.join(AVIS_DIR, "avis_cc_appli_comptoir.txt"),
    'cc_appli_drive': os.path.join(AVIS_DIR, "avis_cc_appli_drive.txt"),
    'cc_appli_guichet': os.path.join(AVIS_DIR, "avis_cc_appli_guichet_exterieur.txt"),
    'cc_appli_exterieur': os.path.join(AVIS_DIR, "avis_cc_appli_exterieur.txt"),
    'cc_site_comptoir': os.path.join(AVIS_DIR, "avis_cc_site_comptoir.txt"),
    'cc_site_drive': os.path.join(AVIS_DIR, "avis_cc_site_drive.txt"),
    'cc_site_exterieur': os.path.join(AVIS_DIR, "avis_cc_site_exterieur.txt"),
    'cc_site_guichet': os.path.join(AVIS_DIR, "avis_cc_site_guichet.txt"),
    'cc_site_guichet_vente': os.path.join(AVIS_DIR, "avis_cc_site_guichet_vente.txt")
}

# Mapping des types de service
SERVICE_TYPE_MAPPING = {
    0: {
        "sur_place": "borne_sur_place",
        "emporter": "borne_emporter"
    },
    1: {
        "sur_place": "comptoir_sur_place",
        "emporter": "comptoir_emporter"
    },
    2: {
        "default": "drive"
    },
    3: {
        "comptoir": "cc_appli_comptoir",
        "drive": "cc_appli_drive",
        "guichet": "cc_appli_guichet",
        "exterieur": "cc_appli_exterieur"
    },
    4: {
        "comptoir": "cc_site_comptoir",
        "drive": "cc_site_drive",
        "guichet": "cc_site_guichet",
        "exterieur": "cc_site_exterieur"
    }
}

RESTAURANT_NUMBER = os.getenv('RESTAURANT_NUMBER', '1435')

SURVEY_URL = os.getenv('SURVEY_URL', 'https://survey2.medallia.eu/?hellomcdo')
