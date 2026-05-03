from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "email_verification_token" VARCHAR(128);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "email_verification_token";"""


MODELS_STATE = (
    "eJztmG1P2zAQgP+KlU9MYh10wNA0TWp50ToNili7TRtT5MZOauHYXewMEOO/785NmiZtOg"
    "qUiWlfquZe/PLc2T772os149I0+oYn3mty7Skac/hTkq8Tj45GhRQFlg6kM0xzi4GxCQ0s"
    "yEIqDQcR4yZIxMgKrdCyTY0ICNoT1w4JdUJoaodcWRFQNCNUMbJ32t9vYJNMB9CmUNHS3m"
    "fqTB1qKfWFIWBBoJk0sGnCSZjo2IkOqbGtk45r8QW2Q6JUwIhfn6nnJFXiR8qdDoGQtYAq"
    "MuAkGFIVcUasJjymQhJJLU+eocuQmiFoRtSYC50w6FIn8C0U2W+jXhgf6IifMARJIzd6o0"
    "NLGHdiNwGc9Lhr3+qIwzAxKN++g1goxi+5yT9H534ouGSlmAmGDTi5b69GTtbvd/YPnSUC"
    "HfiBlmmsCuvRlR1qNTFPgUEDfVAXccUTmCCbiqlKpcxCn4vGIwYBQOaTobJCwHhIU4mZ4b"
    "0JUxW4WLme8GfrrTeTK9hLJQEyUaAV5plQFllc34xnVczZST3sau9d63Tt5c4zN0ttbJQ4"
    "pSPi3ThHaunY1XEtQAYJx2n71M4C3QeNFTGfD7XsWYHLMtdG/ucukHNBQblYbjnmHN/dmH"
    "owB9ZV8iqL4ALGvc7Rwcde6+gEZxIb80M6RK3eAWqaTnpVka6NQ6JhsxjvIJNGyOdO7x3B"
    "T/K1e3xQDdzErvfVwzHBotW+0hc+ZVPJlktzMGBZBDZf0LNh3RvSZH5Ip30qAQVqq1kn9w"
    "xgTC99yVVkh/C52dxdEMFPrVO3UMCqEpbjTNUc625KIEPo2F+WZMnpTigzUI+5GEosm9s7"
    "t2AJVrUsna7M0p0ky3CcODwIw8fNxpUQHJ+9fn72LsNyjuv/zMy5RlpHkvvz6op6oiWnJ5"
    "ihK9kvJ9XfLMm21pJTVVOkTftVYA7AcVUVxITwQ1dl7W73Q6lYaHd6FY79o/YBAHZ4wUhY"
    "J+4c9+btm/5PnogwuwBA1XzO1dJbaU0bT3IfWEn2mkBjKzNc33/sHs/nWnhUa2ARWPKLSG"
    "HsqnJ36pIxSIW0QpkG9reiewZCKGV0jnLtqPWlSnnvQ7ddrWuxgTYQx3tdeD51IUHBgAbn"
    "FzRh/oxGN3Wd7awqbsZVCVU0cgRxxji/7MrfgsUQDL05jwGZZn3RcwAtbP70IFAP/4HvwB"
    "1ll7gCQ8irmZkt6r9a00fYy/Pm5tarrd2XO1u7YOJGMpG8WpCj+eZZf+WFLdBkLxC33Tun"
    "XB7mXvT4NdP2rWqm7QU103Z1r8SlsQTEzPxpAtzc2LjNYbOxUX/YoK4MEHq0XM15eak/ba"
    "ZcHv+4uR/Qf/5gufkN/+syxA=="
)
