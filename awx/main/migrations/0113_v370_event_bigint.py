# Generated by Django 2.2.8 on 2020-02-21 16:31

from django.db import migrations, models, connection


def migrate_event_data(apps, schema_editor):
    # see: https://github.com/ansible/awx/issues/6010
    #
    # the goal of this function is to end with event tables (e.g., main_jobevent)
    # that have a bigint primary key (because the old usage of an integer
    # numeric isn't enough, as its range is about 2.1B, see:
    # https://www.postgresql.org/docs/9.1/datatype-numeric.html)

    # unfortunately, we can't do this with a simple ALTER TABLE, because
    # for tables with hundreds of millions or billions of rows, the ALTER TABLE
    # can take *hours* on modest hardware.
    #
    # the approach in this migration means that post-migration, event data will
    # *not* immediately show up, but will be repopulated over time progressively
    # the trade-off here is not having to wait hours for the full data migration
    # before you can start and run AWX again (including new playbook runs)
    for tblname in ('main_jobevent', 'main_inventoryupdateevent', 'main_projectupdateevent', 'main_adhoccommandevent', 'main_systemjobevent'):
        with connection.cursor() as cursor:
            # rename the current event table
            cursor.execute(f'ALTER TABLE {tblname} RENAME TO _old_{tblname};')
            # create a *new* table with the same schema
            cursor.execute(f'CREATE TABLE {tblname} (LIKE _old_{tblname} INCLUDING ALL);')
            # alter the *new* table so that the primary key is a big int
            cursor.execute(f'ALTER TABLE {tblname} ALTER COLUMN id TYPE bigint USING id::bigint;')

            # recreate counter for the new table's primary key to
            # start where the *old* table left off (we have to do this because the
            # counter changed from an int to a bigint)
            cursor.execute(f'DROP SEQUENCE IF EXISTS "{tblname}_id_seq" CASCADE;')
            cursor.execute(f'CREATE SEQUENCE "{tblname}_id_seq";')
            cursor.execute(f'ALTER TABLE "{tblname}" ALTER COLUMN "id" ' f"SET DEFAULT nextval('{tblname}_id_seq');")
            cursor.execute(f"SELECT setval('{tblname}_id_seq', (SELECT MAX(id) FROM _old_{tblname}), true);")

            # replace the BTREE index on main_jobevent.job_id with
            # a BRIN index to drastically improve per-UJ lookup performance
            # see: https://info.crunchydata.com/blog/postgresql-brin-indexes-big-data-performance-with-minimal-storage
            if tblname == 'main_jobevent':
                cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename='main_jobevent' AND indexdef LIKE '%USING btree (job_id)';")
                old_index = cursor.fetchone()[0]
                cursor.execute(f'DROP INDEX {old_index}')
                cursor.execute('CREATE INDEX main_jobevent_job_id_brin_idx ON main_jobevent USING brin (job_id);')

            # remove all of the indexes and constraints from the old table
            # (they just slow down the data migration)
            cursor.execute(f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename='_old_{tblname}' AND indexname != '{tblname}_pkey';")
            indexes = cursor.fetchall()

            cursor.execute(
                f"SELECT conname, contype, pg_catalog.pg_get_constraintdef(r.oid, true) as condef FROM pg_catalog.pg_constraint r WHERE r.conrelid = '_old_{tblname}'::regclass AND conname != '{tblname}_pkey';"
            )
            constraints = cursor.fetchall()

            for indexname, indexdef in indexes:
                cursor.execute(f'DROP INDEX IF EXISTS {indexname}')
            for conname, contype, condef in constraints:
                cursor.execute(f'ALTER TABLE _old_{tblname} DROP CONSTRAINT IF EXISTS {conname}')


class FakeAlterField(migrations.AlterField):
    def database_forwards(self, *args):
        # this is intentionally left blank, because we're
        # going to accomplish the migration with some custom raw SQL
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0112_v370_workflow_node_identifier'),
    ]

    operations = [
        migrations.RunPython(migrate_event_data),
        FakeAlterField(
            model_name='adhoccommandevent',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        FakeAlterField(
            model_name='inventoryupdateevent',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        FakeAlterField(
            model_name='jobevent',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        FakeAlterField(
            model_name='projectupdateevent',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        FakeAlterField(
            model_name='systemjobevent',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
