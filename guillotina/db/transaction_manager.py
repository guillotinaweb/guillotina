from asyncio import shield
from guillotina.db import ROOT_ID
from guillotina.db.transaction import Transaction
from guillotina.exceptions import ConflictError
from guillotina.exceptions import RequestNotFound
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import get_current_request

import logging


logger = logging.getLogger('guillotina')


class TransactionManager(object):
    """
    Transaction manager for storing the managed transaction in the
    current request object.
    """

    def __init__(self, storage):
        # Guillotine Storage
        self._storage = storage
        # Last transaction created
        self._last_txn = None
        # Pool of transactions
        self._last_db_conn = None

    async def get_root(self, txn=None):
        if txn is None:
            txn = self._last_txn
        return await txn.get(ROOT_ID)

    async def begin(self, request=None):
        """Starts a new transaction.
        """

        db_conn = self._last_db_conn = await self._storage.open()

        if request is None:
            try:
                request = get_current_request()
            except RequestNotFound:
                pass

        user = None

        # if hasattr(request, '_txn'):
        #     # already has txn registered, close connection on it...
        #     await self._close_txn(request._txn)

        self._last_txn = txn = Transaction(self, request=request)

        if request is not None:
            # register tm and txn with request
            request._tm = self
            request._txn = txn
            user = get_authenticated_user_id(request)

        # CACHE!!

        if user is not None:
            txn.user = user
        await txn.tpc_begin(db_conn)

        return txn

    async def commit(self, request=None, txn=None):
        return await shield(self._commit(request=request, txn=txn))

    async def _commit(self, request=None, txn=None):
        """ Commit the last transaction
        """
        if txn is None:
            txn = self.get(request=request)
        if txn is not None:
            try:
                await txn.commit()
            except ConflictError:
                # we're okay with ConflictError being handled...
                raise
            except Exception:
                logger.error('Error committing transaction {}'.format(txn._tid),
                             exc_info=True)
            finally:
                await self._close_txn(txn)
        else:
            await self._close_txn(txn)

    async def _close_txn(self, txn):
        if txn is not None:
            await self._storage.close(txn._db_conn)
        if txn == self._last_txn:
            self._last_txn = None
            self._last_db_conn = None

    async def abort(self, request=None, txn=None):
        return await shield(self._abort(request=request, txn=txn))

    async def _abort(self, request=None, txn=None):
        """ Abort the last transaction
        """
        if txn is None:
            txn = self.get(request=request)
        if txn is not None:
            await txn.abort()
        await self._close_txn(txn)

    def get(self, request=None):
        """Return the current request specific transaction
        """
        if request is None:
            try:
                request = get_current_request()
            except RequestNotFound:
                pass
        if request is None:
            return self._last_txn
        return request._txn
