from backend.auth.middleware import require_role
from backend.models.user import UserRole

require_admin = require_role(UserRole.ADMIN)
require_power_user = require_role(UserRole.ADMIN, UserRole.POWER_USER)
require_any_user = require_role(UserRole.ADMIN, UserRole.POWER_USER, UserRole.BASIC_USER)
