"""Constants for the Kokonna integration."""

DOMAIN = "kokonna"

# API endpoints
API_BASE = "https://api.galaxyguide.cn/openapi"
API_DEVICE = f"{API_BASE}/device"
API_LIST_IMAGES = f"{API_BASE}/listImages"
API_DISPLAY_IMAGE = f"{API_BASE}/displayImageById"
API_IMAGE_BASE = "https://api.galaxyguide.cn/openapi/image"

# Default scan interval (seconds)
DEFAULT_SCAN_INTERVAL = 60

# Attributes
ATTR_DEVICE_ID = "device_id"
ATTR_IMAGE_ID = "image_id"

# Services
SERVICE_SET_IMAGE = "set_image"