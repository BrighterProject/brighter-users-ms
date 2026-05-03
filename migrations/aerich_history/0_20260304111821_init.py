from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "username" VARCHAR(128) NOT NULL UNIQUE,
    "full_name" VARCHAR(256),
    "email" VARCHAR(256) UNIQUE,
    "hashed_password" VARCHAR(256),
    "google_id" VARCHAR(128) UNIQUE,
    "is_active" BOOL NOT NULL DEFAULT True,
    "scopes" JSONB NOT NULL
);
COMMENT ON TABLE "user" IS 'Basic user model for authentication and CRUD.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmOtv0zAQwP8VK582iZWtezBNCKndQxSxdtpaQDAUubGTWnPsEjsb09j/zp2bNE36YB"
    "3rEIgvVXIPP353zp1758WacWlqPcMT74DceYrGHB5K8hfEo8NhIUWBpX3pDNPcom9sQgML"
    "spBKw0HEuAkSMbRCK7RsUiMCgvbEjUNCnRCa2gFXVgQUzQhVjBye945qOCTTAYwpVLS096"
    "W6VCdaSn1jCFgQGCYNbJpwEiY6dqITamzjrOVGfInjkCgVsOKDS7VBUiW+pdzpEAhZC6gi"
    "fU6CAVURZ8RqwmMqJJHU8mQdXQbUDEAzpMbc6ITBlDqBd6HIURP1wvhAR1zDEiSN3OqNDi"
    "1h3IndBnDTo6l9qyMOy8SgfPkKYqEY/85N/jq88kPBJSvFTDAcwMl9ezt0sl6vdXTiLBFo"
    "3w+0TGNVWA9v7UCrsXkKDGrog7qIK57ABtlETFUqZRb6XDRaMQgAMh8vlRUCxkOaSswM73"
    "WYqsDFys2EPztvvKlcwVkqCZCJAq0wz4SyyOLufrSrYs9O6uFUh28b52vbe+tul9rYKHFK"
    "R8S7d47U0pGr41qADBKO2/apnQZ6BBorYj4batmzApdlrrX84TGQc0FBuThuOeYc3+OYer"
    "AH1lHyNovgAsbd1unxRbdxeoY7iY35Jh2iRvcYNXUnva1I10Yh0fCxGH1BxoOQj63uW4Kv"
    "5HOnfVwN3Niu+9nDNcGh1b7SNz5lE8mWS3MwYFkENj/Q02E9HNBkdkgnfSoBBWqrOSe/Gc"
    "CYfvclV5EdwOtWfX9BBD80zt1BAatKWNqZqj7S3ZdAhjCxvyzJktOjUGagnvMwlFjWd/ce"
    "wBKs5rJ0ujJLV0mW4Th2eBKGz5uNKyE4qr1+XnuXYTnD9X9m5lwjrSPJ/Vl9xXyiJae/ME"
    "NX8r0cd3/TJJtaS07VnCZt0q8Csw+Oq+ogxoSfuitrdjrvS81Cs9WtcOydNo8BsMMLRsI6"
    "cavdrTA1gcaRp4C+u+i0Z9MsPKqdmQgs+UGkMHZVRCda334qpBXK1HC+FXW/CKHEOU/Ptd"
    "PGp2rmHr7vNKvdFg7QBOJ42wivJtpkFPRpcHVDE+ZPaXRdz7OdVsX1uCqhikaOIO4Y95dd"
    "RBs8EcHAm3FFzTQvFl1SaWHzq2vqfPhPfDNrKbvExQxCXs3M7Iz+0U4zwlk26ls7r3b2t/"
    "d29sHErWQsebUgR/MjPf8ids0Tk92LH1p+Jlyeplt//kq++6BKvrugku9W6w8ejSUgZuZ/"
    "J8Ctzc2HFPDNzfkFHHVlgDCj5WrG/wHzq82Ey/OXm98D+s8Xlvufxb28cQ=="
)
