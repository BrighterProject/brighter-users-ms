from tortoise import migrations


class Migration(migrations.Migration):
    dependencies = [('models', '0002_auto_20260504_0137')]

    initial = False

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE "user"
                ADD COLUMN IF NOT EXISTS "locale" VARCHAR(10) NOT NULL DEFAULT 'en';
            """,
            reverse_sql='ALTER TABLE "user" DROP COLUMN IF EXISTS "locale";',
        ),
    ]
