.PHONY: flake8 test coverage style style_check

style:
	black --target-version=py36 database_locks tests setup.py
	flake8 database_locks tests

style_check:
	black --target-version=py36 --check database_locks tests setup.py

flake8:
	flake8 database_locks tests

startmysql:
	docker inspect django-database-locks-mysql | grep '"Running": true' || \
		docker run --name django-database-locks-mysql \
		           -e MYSQL_ROOT_PASSWORD=root \
		           --rm -p 8877:3306 -d \
				   --health-cmd "mysqladmin ping" \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries=5 \
				   mysql:5
	# TODO: wait for healthy

startpg:
	docker inspect django-database-locks-pg | grep '"Running": true' || \
		docker run --name django-database-locks-pg \
		           -e POSTGRES_USER=postgres \
          		   -e POSTGRES_PASSWORD=postgres \
				   -e POSTGRES_DB=postgres \
		           --rm -p 8878:5432 -d \
				   --health-cmd pg_isready \
				   --health-interval 10s \
				   --health-timeout 5s \
				   --health-retries 5 \
				   postgres:10
	# TODO: wait for healthy

test: startmysql
	DJANGO_SETTINGS_MODULE=settings_mysql \
		tests/manage.py test $${TEST_ARGS:-tests}

testpg: startpg
	DJANGO_SETTINGS_MODULE=settings_postgresql \
		tests/manage.py test $${TEST_ARGS:-tests}

testcover: export DJANGO_SETTINGS_MODULE=settings_mysql
testcover: startmysql
testcover: coverage

coverage:
	python --version
	coverage erase
	PYTHONPATH="tests" \
		python -b -W always -m coverage run tests/manage.py test $${TEST_ARGS:-tests}
	coverage report
