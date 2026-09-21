"""Merge a local SQLite workspace into a migrated database, preserving target rows.

Run explicitly after backing up the target; all inserted records commit atomically.
Existing matches are retained, including profile blocks. Source IDs are remapped.
"""
import argparse
import os
from sqlalchemy import MetaData, create_engine, select, and_, Boolean

TABLES = ['profile_blocks', 'companies', 'applications', 'job_offers', 'job_analyses',
          'email_events', 'gmail_sync_states', 'opportunities', 'opportunity_links', 'opportunity_events']
IDENTITIES = {
    'profile_blocks': ('title', 'content'), 'companies': ('name',),
    'applications': ('telegram_user_id', 'source_url', 'raw_offer'),
    'job_offers': ('job_url',), 'job_analyses': ('application_id', 'analysis_json'),
    'email_events': ('owner_id', 'mailbox', 'gmail_message_id'),
    'gmail_sync_states': ('owner_id',), 'opportunities': ('owner_id', 'canonical_key'),
    'opportunity_links': ('source_type', 'source_id'),
    'opportunity_events': ('opportunity_id', 'event_type', 'source_type', 'source_id'),
}
SOURCE_TABLES = {'application': 'applications', 'job_offer': 'job_offers', 'email_event': 'email_events'}


def merge_workspace(source, target, owner):
    src, dst = MetaData(), MetaData()
    src.reflect(source)
    dst.reflect(target)
    maps, counts = {}, {}
    with source.connect() as reader, target.begin() as writer:
        for name in TABLES:
            st, dt = src.tables[name], dst.tables[name]
            maps[name] = {}
            added = 0
            for record in reader.execute(select(st)).mappings():
                values = {k: v for k, v in record.items() if k in dt.c and k != 'id'}
                for key in ('owner_id', 'telegram_user_id'):
                    if values.get(key) == 'local':
                        values[key] = owner
                for column in dt.c:
                    if isinstance(column.type, Boolean) and values.get(column.name) is not None:
                        values[column.name] = bool(values[column.name])
                    for fk in column.foreign_keys:
                        old = values.get(column.name)
                        if old is not None:
                            values[column.name] = maps[fk.column.table.name][old]
                if name in ('opportunity_links', 'opportunity_events'):
                    kind = SOURCE_TABLES[values['source_type']]
                    values['source_id'] = maps[kind][values['source_id']]
                keys = IDENTITIES[name]
                # PostgreSQL JSON has no equality operator. Each source application
                # has at most one imported analysis, while existing analyses win.
                if name == 'job_analyses':
                    keys = ('application_id',)
                query = select(dt).where(and_(*(dt.c[k] == values[k] for k in keys)))
                existing = writer.execute(query).mappings().first()
                pk = 'id' if 'id' in dt.c else 'owner_id'
                if existing:
                    new_id = existing[pk]
                else:
                    new_id = writer.execute(dt.insert().values(**values).returning(dt.c[pk])).scalar_one()
                    added += 1
                if 'id' in record:
                    maps[name][record['id']] = new_id
            counts[name] = added
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sqlite_file')
    parser.add_argument('--owner', required=True)
    args = parser.parse_args()
    source = create_engine('sqlite:///' + os.path.abspath(args.sqlite_file))
    target = create_engine(os.environ['DATABASE_URL'])
    try:
        print(merge_workspace(source, target, args.owner))
    finally:
        source.dispose()
        target.dispose()
