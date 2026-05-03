from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('models', '0001_initial')]

    initial = False

    operations = [
        ops.AddField(
            model_name='User',
            name='company_name',
            field=fields.CharField(null=True, max_length=256),
        ),
        ops.AddField(
            model_name='User',
            name='phone',
            field=fields.CharField(null=True, max_length=30),
        ),
    ]
