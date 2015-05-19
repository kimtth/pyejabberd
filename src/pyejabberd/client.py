# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import xmlrpclib
import copy

from . import contract, definitions
from .core.definitions import API, APIArgument
from .core.errors import IllegalArgumentError


# noinspection PyTypeChecker
class EjabberdAPIClient(contract.EjabberdAPIContract):
    """
    Python Client for the Ejabberd XML-RPC API
    """
    def __init__(self, host, port, username, password, xmpp_domain, muc_service="conference", protocol='https',
                 verbose=False):
        """
        Constructor
        :param host:
        :type host: str
        :param port:
        :type port: int
        :param username:
        :type username: str
        :param password:
        :type password: str
        :param xmpp_domain:
        :type xmpp_domain: str
        :param muc_service:
        :type muc_service: str
        :param protocol:
        :type protocol: str
        :param verbose:
        :type verbose: bool
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.xmpp_domain = xmpp_domain
        self.muc_service = muc_service
        self.protocol = protocol
        self.verbose = verbose

    @property
    def service_url(self):
        """
        Returns the FQDN to the Ejabberd server's XML-RPC endpoint
        :return:
        """
        return "%s://%s:%s/" % (self.protocol, self.host, self.port)

    @property
    def proxy(self):
        """
        Returns the proxy object that is used to perform the calls to the XML-RPC endpoint
        :rtype: :py:class:xmlrpclib.ServerProxy
        :return the proxy object that is used to perform the calls to the XML-RPC endpoint
        """
        return xmlrpclib.ServerProxy(self.service_url, verbose=(1 if self.verbose else 0))

    @property
    def auth(self):
        """
        Returns a dictionary containing the basic authorization info
        :rtype: dict
        :return: a dictionary containing the basic authorization info
        """
        return {
            'user': self.username,
            'server': self.xmpp_domain,
            'password': self.password
        }

    @property
    def context(self):
        """
        Returns a generic context object containing client XMPP info
        :rtype: dict
        :return: a generic context object containing client XMPP info
        """
        return {
            'host': self.xmpp_domain,
            'service': self.muc_service
        }

    def echo(self, sentence):
        """
        Echo's the input back
        :param sentence:
        :type sentence: str
        :rtype: str
        :return: The echoed response, which should be the same as the input
        """
        return self._call_api(definitions.Echo, sentence=sentence)

    def registered_users(self):
        """
        List all registered users in the xmpp_host
        :rtype: Iterable
        :return: A list of registered users in the xmpp_host
        """
        return self._call_api(definitions.RegisteredUsers)

    def register(self, user, password):
        """
        Registers a user to the ejabberd server
        :param user: The username for the new user
        :type user: str
        :param password: The password for the new user
        :type password: str
        :rtype: bool
        :return: Returns a boolean indicating if the registration has succeeded
        """
        return self._call_api(definitions.Register, user=user, password=password)

    def unregister(self, user):
        """
        UnRegisters a user from the ejabberd server
        :param user: The username for the new user
        :type user: str
        :rtype: bool
        :return: Returns a boolean indicating if the unregistration has succeeded
        """
        return self._call_api(definitions.UnRegister, user=user)

    def change_password(self, user, newpass):
        """
        Change the password for a given user
        :param user: The username for the user we want to change the password for
        :type user: str
        :param newpass: The new password
        :type newpass: str
        :rtype: bool
        :return: Returns a boolean indicating if the password change has succeeded
        """
        return self._call_api(definitions.ChangePassword, user=user, newpass=newpass)

    def check_password_hash(self, user, password):
        """
        Checks whether a password is correct for a given user. The used hash-method is fixed to sha1.
        :param user: The username for the user we want to check the password for
        :type user: str
        :param password: The password we want to check for the user
        :type password: str
        :rtype: bool
        :return: Returns a boolean indicating if the given password matches the user's password
        """
        return self._call_api(definitions.CheckPasswordHash, user=user, password=password)

    def set_nickname(self, user, nickname):
        """
        Set nickname in a user's vCard
        :param user: The username for the user we want to set the nickname to
        :type user: str
        :param nickname: The nickname to assign to the user
        :type nickname: str
        :rtype: bool
        :return: Returns a boolean indicating nickname was assigned successfully
        """
        return self._call_api(definitions.SetNickname, user=user, nickname=nickname)

    def _call_api(self, api_class, **kwargs):
        """
        Internal method used to perform api calls
        :param api_class:
        :type api_class: py:class:API
        :param kwargs:
        :type kwargs: dict
        :return:
        """
        # Validate api_class
        assert issubclass(api_class, API)

        # Create api instance
        api = api_class()

        # Copy arguments
        arguments = copy.copy(kwargs)

        # Transform arguments
        arguments = api.transform_arguments(self.context, **arguments)

        # Validate arguments
        for argument_descriptor in api.arguments:
            assert isinstance(argument_descriptor, APIArgument)

            # Validate argument presence
            argument_name = str(argument_descriptor.name)
            if argument_descriptor.required and argument_name not in arguments:
                raise IllegalArgumentError('Missing required argument "%s"' % argument_name)

            # Validate argument value
            argument_descriptor.validator_class().validate(arguments.get(argument_name))

        # Retrieve method
        method = getattr(self.proxy, api.method)

        # Perform call
        if not api.authenticate:
            response = method(arguments)
        else:
            response = method(self.auth, arguments)

        # Validate response
        api.validate_response(self.context, api, arguments, response)

        # Transform response
        result = api.transform_response(self.context, api, arguments, response)

        return result
