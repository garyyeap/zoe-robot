"""
kalapy.db.engines.interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module defines the database interface to be implemented by backend engines.
The implementation is meant for internal use only. Users should use Model API
instead.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""

class IDatabase(object):
    """The database interface. Backend engines should implement this class
    with name `Database`.

    :param name: the name of the database
    :param host: the hostname where the database server is running
    :param port: the port on which the database server is listening
    :param user: the user name to connect to the database
    :param password: the database password
    """

    #: mimetype of return value of :meth:`schema_table`.
    schema_mime = "text/plain"

    def __init__(self, name, host=None, port=None, user=None, password=None):
        """Initialize the database.
        """
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def connect(self):
        """Connect to the database.
        """
        raise NotImplementedError

    def close(self):
        """Close the database connection.
        """
        raise NotImplementedError

    def commit(self):
        """Commit the changes to the database.
        """
        raise NotImplementedError

    def rollback(self):
        """Rollback all the changes made since the last commit.
        """
        raise NotImplementedError
    
    def run_in_transaction(self, func, *args, **kw):
        """A helper function to run the specified func in a transaction. This
        function is provided as a convenient method to manage transaction by
        some database engines, especially the GAE engine.
        
        Example usage::
            
            def some_function(a, b, c):
                u = User(name="some")
                u.lang = "fr_FR"
                u.save()
                
            db.run_in_transaction(some_function, 1, 2, c=4)
            
        :param func: the callable to be run in transaction
        :param args: positional arguments to be passed to the function
        :param kw: keyword arguments to be passed to the function
        
        :returns: result of the function
        :raises: any exception thrown during function execution
        """
        try:
            res = func(*args, **kw)
        except:
            self.rollback()
            raise
        else:
            self.commit()
        return res

    def schema_table(self, model):
        """Returns the schema information of the table for the given model.

        :param model: a subclass of :class:`Model`

        :returns: textual representaion of the model in the database
        """
        raise NotImplementedError

    def exists_table(self, model):
        """Check whether the table exists or not.

        :param model: a subclass of :class:`Model`

        :returns: True if table exists else False
        """
        raise NotImplementedError

    def create_table(self, model):
        """Create a table for the given model if it doesn't exist.

        :param model: a subclass of :class:`Model`
        """
        raise NotImplementedError

    def alter_table(self, model, name=None):
        """Alter the table associated for the given model. If name is given look
        for the table by that name (if model class name has been changed).

        :param model: a subclass of :class:`Model`
        :param name: if given, should be the name of table
        """
        raise NotImplementedError

    def drop_table(self, model):
        """Drop the table

        :param model: a subclass of :class:`Model`
        """
        raise NotImplementedError

    def update_records(self, instance, *args):
        """Update database records for the given model instances.

        The implementation should take care of:

            - Inserting records if records doesn't exist.
            - Updating `key` value of the given model instances.

        :param instance: an instance of :class:`Model` subclass
        :param args: more instances

        :returns: list of key values
        :raises:
            - :class:`DatabaseError`
            - :class:`IntegrityError`
        """
        raise NotImplementedError

    def delete_records(self, instance, *args):
        """Delete database records for the given model instances. This method
        also accepts keys.

        The implementation should take care of:

            - Updating `key` value of the given model instances to None.

        :param instance: a Model instance or a record key
        :param args: more Model instances or record keys

        :returns: list of key values which have been deleted.
        :raises:
            - :class:`DatabaseError`
            - :class:`IntegrityError`
        """
        raise NotImplementedError

    def fetch(self, qset, limit, offset):
        """Fetch records from database filtered by the given query set bound
        to given limit and offset.

        For more information on query set, see :class:`db.query.QSet`.

        The implementation should return an iterator or generator of dict
        having ``name``, ``value`` mapping including ``key`` information.

        Database engine specific information can be passed with ``_payload``
        which will be stored as an attribute to the model instance.

        :param qset: the query set, an instance of :class:`db.query.QSet`
        :param limit: number of records to be fetch
        :param offset: offset from where to fetch records

        :returns: an interator of dict of name, value mappings
        :raises:
            - :class:`db.DatabaseError`
        """
        raise NotImplementedError

    def count(self, qset):
        """Returns the total number of records matched by given query set.

        :param qset: the query set, an instance of :class:`db.query.QSet`

        :returns: integer, total number of records
        :raises:
            - :class:`DatabaseError`
        """
        raise NotImplementedError

