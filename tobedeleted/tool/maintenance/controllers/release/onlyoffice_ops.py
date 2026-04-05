from ._shared import _tool_mod, _delegate

def deploy_onlyoffice_to_test(app, *args, **kwargs):
    return _delegate(app, "_deploy_onlyoffice_to_test_impl", "deploy_onlyoffice_to_test", *args, **kwargs)

def deploy_onlyoffice_to_test_impl(app):
    tool_mod = _tool_mod()
    self = app
    TEST_SERVER_IP = tool_mod.TEST_SERVER_IP

    self._deploy_onlyoffice_to_server(server_ip=TEST_SERVER_IP, display_name="测试")

def deploy_onlyoffice_to_prod(app, *args, **kwargs):
    return _delegate(app, "_deploy_onlyoffice_to_prod_impl", "deploy_onlyoffice_to_prod", *args, **kwargs)

def deploy_onlyoffice_to_prod_impl(app):
    tool_mod = _tool_mod()
    self = app
    PROD_SERVER_IP = tool_mod.PROD_SERVER_IP

    self._deploy_onlyoffice_to_server(server_ip=PROD_SERVER_IP, display_name="正式")
