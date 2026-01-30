from marshmallow import Schema, fields, validate


class AddProductSchema(Schema):
    """Schema for adding a new product"""
    user_id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "User ID who owns the product",
            "example": 1
        }
    )
    url = fields.Str(
        required=True,
        validate=validate.URL(),
        metadata={
            "description": "Amazon product URL",
            "example": "https://www.amazon.in/dp/B08XYZ1234"
        }
    )
    threshold = fields.Float(
        required=True,
        validate=validate.Range(min=0),
        metadata={
            "description": "Price threshold in ₹ (rupees). Alert will be sent when price drops to or below this value",
            "example": 5000.0
        }
    )


class RemoveProductSchema(Schema):
    """Schema for removing a product"""
    user_id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "User ID who owns the product",
            "example": 1
        }
    )
    id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "Amazon product to be removed from tracking",
            "example": 1
        }
    )


class CheckPriceSchema(Schema):
    """Schema for checking price of a product"""
    user_id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "User ID who owns the product",
            "example": 1
        }
    )
    url = fields.Str(
        required=True,
        validate=validate.URL(),
        metadata={
            "description": "Amazon product URL to check price for",
            "example": "https://www.amazon.in/dp/B08XYZ1234"
        }
    )


class UpdateNotificationsSchema(Schema):
    """Schema for updating notification settings"""
    user_id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "User ID whose notification settings to update",
            "example": 1
        }
    )
    email = fields.Email(
        required=False,
        allow_none=True,
        metadata={
            "description": "Email address for price drop notifications",
            "example": "user@example.com"
        }
    )
    phone_number = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Regexp(r'^\+?[1-9]\d{1,14}$', error="Phone number must be in international format (e.g., +919876543210)"),
        metadata={
            "description": "Phone number in international format for WhatsApp notifications",
            "example": "+919876543210"
        }
    )


class SendNotificationSchema(Schema):
    """Schema for sending a notification manually"""
    user_id = fields.Int(
        required=True,
        strict=True,
        metadata={
            "description": "User ID whose notification channels to use",
            "example": 1
        }
    )
    title = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": "Product title/name",
            "example": "Samsung Galaxy S21"
        }
    )
    url = fields.Str(
        required=True,
        validate=validate.URL(),
        metadata={
            "description": "Amazon product URL",
            "example": "https://www.amazon.in/dp/B08XYZ1234"
        }
    )


# Response schemas for documentation
class ProductSchema(Schema):
    """Schema for product response"""
    url = fields.Str(metadata={"description": "Product URL"})
    threshold = fields.Float(metadata={"description": "Price threshold"})
    title = fields.Str(metadata={"description": "Product title"})
    current_price = fields.Float(metadata={"description": "Current price"})


class NotificationSettingsSchema(Schema):
    """Schema for notification settings response"""
    email = fields.Str(metadata={"description": "Email address"})
    # phone_number = fields.Str(metadata={"description": "Phone number"})


class SuccessResponseSchema(Schema):
    """Schema for success response"""
    success = fields.Bool(metadata={"description": "Whether the operation was successful"})
    message = fields.Str(metadata={"description": "Response message"})


class ErrorResponseSchema(Schema):
    """Schema for error response"""
    success = fields.Bool(metadata={"description": "Always false for errors"})
    error = fields.Str(metadata={"description": "Error message"})
