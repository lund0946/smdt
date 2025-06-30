SESSION_TYPE = 'filesystem'
SESSION_SERIALIZATION_FORMAT = 'json'
SESSION_PERMINANT = True 
SESSION_COOKIE_NAME = 'smdt_session'
SESSION_COOKIE_SAMESITE="None"
SESSION_COOKIE_SECURE = True 
MAX_CONTENT_LENGTH = 104857600 #100*1024*1024
SECRET_KEY = 'dsf2315ewd' # used by sessions to encrypt data. Not really secure, but good enough for local development.