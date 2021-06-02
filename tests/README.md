# tests

This is a django app to run tests on `bulk_update_or_create`.

`manage.py` has been patched to include parent directory in `sys.path` so you can simply run:

```
./manage.py test
```

`pytest.ini` added to make it easier to run tests from IDEs (such as VSCode), thanks to [pytest-django](https://github.com/pytest-dev/pytest-django/).

`pytest` needs to be executed inside this directory (where `manage.py` is) and [requirements.txt](requirements.txt) need to be installed:

```
pip install -r requirements.txt
```

Use `make -f ../Makefile startmysql` to spin up a mysql docker (or set `DJANGO_SETTINGS_MODULE` env var to different settings).


## VSCode

To run/debug the tests in VSCode:

* make sure to open this folder (not parent) as workspace
  * or use multi-project workspaces: open parent and then select "Add Folder to Workspace" and add this one
* select `Python > Configure Tests` and choose `pytest`

:heavy_check_mark:
