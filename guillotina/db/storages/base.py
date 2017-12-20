

class BaseStorage(object):

    _cache_strategy = 'dummy'
    _read_only = False
    _transaction_strategy = 'resolve'

    def __init__(self, read_only=False, transaction_strategy='resolve',
                 cache_strategy='dummy'):
        self._read_only = read_only
        self._transaction_strategy = transaction_strategy
        self._cache_strategy = cache_strategy

    def read_only(self):
        return self._read_only

    async def finalize(self):
        raise NotImplemented()

    async def initialize(self, loop=None, **kw):
        raise NotImplemented()

    async def open(self):
        raise NotImplemented()

    async def close(self, con):
        raise NotImplemented()

    async def load(self, txn, oid):
        raise NotImplemented()

    async def store(self, oid, old_serial, writer, obj, txn):
        raise NotImplemented()

    async def delete(self, txn, oid):
        raise NotImplemented()

    async def get_next_tid(self, txn):
        raise NotImplemented()

    async def get_current_tid(self, txn):
        raise NotImplemented()

    async def get_one_row(self, smt, *args):
        raise NotImplemented()

    async def start_transaction(self, txn, retries=0):
        raise NotImplemented()

    async def get_conflicts(self, txn):
        raise NotImplemented()

    async def commit(self, transaction):
        raise NotImplemented()

    async def abort(self, transaction):
        raise NotImplemented()

    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        raise NotImplemented()

    async def keys(self, txn, oid):
        raise NotImplemented()

    async def get_child(self, txn, parent_oid, id):
        raise NotImplemented()

    async def has_key(self, txn, parent_oid, id):
        raise NotImplemented()

    async def len(self, txn, oid):
        raise NotImplemented()

    async def items(self, txn, oid):
        raise NotImplemented()

    async def get_annotation(self, txn, oid, id):
        raise NotImplemented()

    async def get_annotation_keys(self, txn, oid):
        raise NotImplemented()

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        raise NotImplemented()

    async def read_blob_chunk(self, txn, bid, chunk=0):
        raise NotImplemented()

    async def read_blob_chunks(self, txn, bid):
        raise NotImplemented()

    async def del_blob(self, txn, bid):
        raise NotImplemented()

    async def get_total_number_of_objects(self, txn):
        raise NotImplemented()

    async def get_total_number_of_resources(self, txn):
        raise NotImplemented()

    async def get_total_resources_of_type(self, txn, type_):
        raise NotImplemented()

    async def _get_page_resources_of_type(self, txn, type_, page, page_size):
        raise NotImplemented()
