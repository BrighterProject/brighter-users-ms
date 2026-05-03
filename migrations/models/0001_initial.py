from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from json import dumps, loads
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('username', fields.CharField(unique=True, max_length=128)),
                ('full_name', fields.CharField(null=True, max_length=256)),
                ('email', fields.CharField(null=True, unique=True, max_length=256)),
                ('hashed_password', fields.CharField(null=True, max_length=256)),
                ('google_id', fields.CharField(null=True, unique=True, max_length=128)),
                ('is_active', fields.BooleanField(default=True)),
                ('email_verification_token', fields.CharField(null=True, max_length=128)),
                ('scopes', fields.JSONField(default=list, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
            ],
            options={'table': 'user', 'app': 'models', 'pk_attr': 'id', 'table_description': 'Basic user model for authentication and CRUD.'},
            bases=['AbstractModel'],
        ),
    ]
