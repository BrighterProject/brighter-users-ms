from enum import StrEnum


class UserScope(StrEnum):
    READ = "users:read"
    ME = "users:me"
    ADMIN = "admin:users"


class PropertyScope(StrEnum):
    READ = "properties:read"
    ME = "properties:me"
    WRITE = "properties:write"
    DELETE = "properties:delete"
    IMAGES = "properties:images"
    SCHEDULE = "properties:schedule"

    ADMIN = "admin:properties"
    ADMIN_READ = "admin:properties:read"
    ADMIN_WRITE = "admin:properties:write"
    ADMIN_DELETE = "admin:properties:delete"


class BookingScope(StrEnum):
    # Customer scopes
    READ = "bookings:read"  # view own bookings
    WRITE = "bookings:write"  # create a booking
    CANCEL = "bookings:cancel"  # cancel own booking

    # Property owner scopes
    MANAGE = "bookings:manage"  # confirm / complete / no_show for own property's bookings

    # Admin scopes
    ADMIN = "admin:bookings"
    ADMIN_READ = "admin:bookings:read"
    ADMIN_WRITE = "admin:bookings:write"
    ADMIN_DELETE = "admin:bookings:delete"


class PaymentScope(StrEnum):
    # Customer scopes
    READ = "payments:read"  # view own payment history

    # Admin scopes
    ADMIN = "admin:payments"
    ADMIN_READ = "admin:payments:read"
    ADMIN_WRITE = "admin:payments:write"
    ADMIN_DELETE = "admin:payments:delete"


class NotificationScope(StrEnum):
    ADMIN = "admin:notifications"
    ADMIN_READ = "admin:notifications:read"
    ADMIN_WRITE = "admin:notifications:write"


USER_SCOPES_DESCS: dict[str, str] = {
    UserScope.READ: "Read users data.",
    UserScope.ME: "Read current user profile.",
    UserScope.ADMIN: "Perform any user operation (admin).",
}

PROPERTY_SCOPES_DESCRIPTIONS: dict[str, str] = {
    PropertyScope.READ: "Browse and search public property listings.",
    PropertyScope.ME: "Read your own properties and their details.",
    PropertyScope.WRITE: "Create and update your own properties.",
    PropertyScope.DELETE: "Delete your own properties.",
    PropertyScope.IMAGES: "Upload and manage images for your own properties.",
    PropertyScope.SCHEDULE: "Manage unavailability windows for your own properties.",
    PropertyScope.ADMIN: "Perform any property operation (admin)",
    PropertyScope.ADMIN_READ: "Read any property regardless of status (admin).",
    PropertyScope.ADMIN_WRITE: "Edit any property and change its status (admin).",
    PropertyScope.ADMIN_DELETE: "Hard-delete any property (admin).",
}

BOOKING_SCOPE_DESCRIPTIONS: dict[str, str] = {
    BookingScope.READ: "View your own bookings.",
    BookingScope.WRITE: "Create a new booking at a property.",
    BookingScope.CANCEL: "Cancel your own pending or confirmed booking.",
    BookingScope.MANAGE: "Confirm, complete, or mark no-show on your property bookings.",
    BookingScope.ADMIN_READ: "Read any booking regardless of owner (admin).",
    BookingScope.ADMIN_WRITE: "Modify any booking status (admin).",
    BookingScope.ADMIN_DELETE: "Hard-delete any booking (admin).",
}

PAYMENT_SCOPE_DESCRIPTIONS: dict[str, str] = {
    PaymentScope.READ: "View your own payment history.",
    PaymentScope.ADMIN: "Full access to all payments (admin super-scope).",
    PaymentScope.ADMIN_READ: "Read any payment (admin).",
    PaymentScope.ADMIN_WRITE: "Modify any payment or issue refunds (admin).",
    PaymentScope.ADMIN_DELETE: "Hard-delete any payment record (admin).",
}


NOTIFICATION_SCOPE_DESCRIPTIONS: dict[str, str] = {
    NotificationScope.ADMIN: "Full access to notifications (admin super-scope).",
    NotificationScope.ADMIN_READ: "View notification history (admin).",
    NotificationScope.ADMIN_WRITE: "Send notifications (admin).",
}


SCOPE_DESCS = (
    PROPERTY_SCOPES_DESCRIPTIONS
    | USER_SCOPES_DESCS
    | BOOKING_SCOPE_DESCRIPTIONS
    | PAYMENT_SCOPE_DESCRIPTIONS
    | NOTIFICATION_SCOPE_DESCRIPTIONS
)
DEFAULT_USER_SCOPES = [
    UserScope.ME,
    PropertyScope.READ,
    BookingScope.READ,
    BookingScope.WRITE,
    BookingScope.CANCEL,
    PaymentScope.READ,
]
DEFAULT_OWNER_SCOPES = DEFAULT_USER_SCOPES + [
    PropertyScope.ME,
    PropertyScope.WRITE,
    PropertyScope.DELETE,
    PropertyScope.IMAGES,
    PropertyScope.SCHEDULE,
    BookingScope.MANAGE,
    PaymentScope.READ,
]
DEFAULT_ADMIN_SCOPES = [
    UserScope.ADMIN,
    PropertyScope.ADMIN,
    BookingScope.ADMIN,
    PaymentScope.ADMIN,
    NotificationScope.ADMIN,
]
