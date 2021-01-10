import logging

from datetime import timedelta

NOAUTH_DEBUGMODE = False #put this flag to true if want to enable "not authenticated debug mode". Used only to debug integration without going through authentication and real gams queries in fanatical.
NOAUTH_DEBUGMODE_DATAFILE='debug_data.json' # Used debug integration (ehen NOAUTH_DEBUGMODE is set to true) to have some games to test instead of gettin real games queries in fanatical.
BACKUP_GAMES_DB= False # used when debugging to generate a local jason file *_last containing local list of games. Produyced file can also be be used as NOAUTH_DEBUGMODE_DATAFILE while debugging without logger in to fanatical when NOAUTH_DEBUGMODE is enabled
GAMES_SPECIALS_DATAFILE='games_name_mapping.json' 
#Used to map fanatical names to more commmon ones. File structure is the following:
# [
#     {
#         "Azura": "Azura",
#         "GRID - 2019": "GRID (2019)",
#         "DLC": "__FORCE_EXCLUSION__",
#     }
# ]
#
# key can be a regular expression, that is search end in game name string (the key is case insensitive)
# if mapped to __FORCE_EXCLUSION__ game is not considered in library
#
MIN_LOG_LEVEL = logging.WARNING #Change this to set logging level.

SCRAPED_GAMES_MODE = False #set this to true to get game names scraping them on the renderd HTML DOM and sending them via cookies to GG app
CLOSE_COOKIEPOLICYCONSENT = False #closes cookie policy dialog automatically if set. DO NOT USE because this skips the GDPR/Privacy guidelines requirements Fanical is compliant with. Left here only for historical reasons.
LAZYDOM_MODE = False #True used to have anternave "fixed time waiting machanism" to wait for DOM being generated from react calls, instead of monitoring for DOM elements to be created/present. Usen mainly, but not only, when SCRAPING_MODE is on

CACHEING_GAMES_FLAG = True #This is used to have games updated every OWNED_GAMES_CACHE_TIMEOUT instead of waiting for the GOG client to ask for update. In scraping mode games are not re-scraped but are updated if rescaping happened.
OWNED_GAMES_CACHE_TIMEOUT = timedelta(minutes=15) if not NOAUTH_DEBUGMODE else timedelta(minutes=1) #fifteen minutes between calls but 1 minute while debugging

LANGUAGESTRING='en' #used to form url strings basing on language - only "en" tested and functioning

HOMEPAGE = 'https://www.fanatical.com/' #Fanatical is (currently - as oct 2020) a react based site, so there is not real login page, but a "login component" in all the "pages" 
GAME_PAGE_ROOT = HOMEPAGE+ LANGUAGESTRING +'/game/' # experimental used to point to the detail game page url on fanatical using slug_url. Currently not used
SCRAPING_PAGE = HOMEPAGE+ LANGUAGESTRING +'/product-library?page=1' #used to scrape games when SCRAPED_GAMES_MODE is turned on. Forces to the first page to make navigation pages supposition.
ORDER_PAGE = HOMEPAGE+ LANGUAGESTRING +'/orders' #used as exit point from GG embedded browser when authenticating/scraping (if not in NOAUTH_DEBUGMODE is enabled)
BUNDLE_PAGE = HOMEPAGE+ LANGUAGESTRING +'/bundle' #used as exit point from GG embedded browser when authorization is skipped 

KEYS_URL = HOMEPAGE+'api/user/keys'

HOMEPAGE_URI_REGEX = r"^https://(www\.)*fanatical\.com/"
SCRAPING_URI_REGEX = r"^https://(www\.)*fanatical\.com/../product-library.*"
END_URI_REGEX = r"^https://(www\.)*fanatical\.com/../orders.*" # This is used as reference to exit the GG integrated browser (in authentication mode)
END_URI_REGEX_NOAUTH_DEBUG = r"^https://(www\.)*fanatical\.com/../bundle.*" # This is used as reference to exit the GG integrated browser (in debug/disabled authentication mode)
